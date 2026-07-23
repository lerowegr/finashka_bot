"""ETL: fetch -> parse -> validate -> upsert. Ошибка одной страницы не валит обход."""

import logging
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m
from app.db.engine import session_factory
from app.notify import notify_admin
from app.scraper.client import SiteClient
from app.scraper.parsers.np_page import parse_np_page
from app.scraper.parsers.program_card import parse_program_card
from app.scraper.parsers.programs_list import parse_program_cards
from app.scraper.parsers.sitemap import parse_sitemap
from app.scraper.parsers.vuz_about import parse_vuz_about
from app.scraper.parsers.vuz_dod import parse_vuz_dod
from app.scraper.parsers.vuz_obsh import parse_vuz_obsh
from app.scraper.schemas import OpenDayInfo, ProgramSummary, VuzAbout

log = logging.getLogger(__name__)


class Etl:
    def __init__(self, client: SiteClient | None = None):
        self.client = client or SiteClient()
        self._subject_ids: dict[str, int] = {}

    # ---------- служебное ----------

    async def _start_run(self, kind: str) -> int:
        async with session_factory() as session:
            run = m.ScrapeRun(kind=kind, started_at=datetime.now())
            session.add(run)
            await session.commit()
            return run.id

    async def _finish_run(self, run_id: int, ok: int, failed: int) -> None:
        async with session_factory() as session:
            run = await session.get(m.ScrapeRun, run_id)
            run.finished_at = datetime.now()
            run.pages_ok = ok
            run.pages_failed = failed
            run.status = "ok" if failed == 0 else ("partial" if ok else "failed")
            await session.commit()
        await notify_admin(
            f"ETL <b>{run.kind}</b> завершён: {ok} страниц ок, {failed} с ошибками"
        )

    async def _subject_id(self, session: AsyncSession, name: str) -> int:
        if name not in self._subject_ids:
            subject = (
                await session.execute(select(m.ExamSubject).where(m.ExamSubject.name == name))
            ).scalar_one_or_none()
            if subject is None:
                subject = m.ExamSubject(name=name)
                session.add(subject)
                await session.flush()
            self._subject_ids[name] = subject.id
        return self._subject_ids[name]

    async def _log_change(
        self, session: AsyncSession, entity: str, entity_id: int, field: str, old, new, run_id: int
    ) -> None:
        if old is None or old == new:
            return
        session.add(
            m.ChangeLog(
                entity=entity,
                entity_id=entity_id,
                field=field,
                old_value=str(old),
                new_value=str(new),
                scrape_run_id=run_id,
            )
        )

    # ---------- upsert одного вуза ----------

    async def _upsert_vuz(
        self,
        about: VuzAbout,
        dorm,
        programs: list[ProgramSummary],
        open_days: list[OpenDayInfo],
        run_id: int,
    ) -> None:
        now = datetime.now()
        async with session_factory() as session:
            region_id = None
            if about.region_name:
                region = (
                    await session.execute(
                        select(m.Region).where(m.Region.name == about.region_name)
                    )
                ).scalar_one_or_none()
                if region is None:
                    region = m.Region(name=about.region_name, slug=about.region_slug)
                    session.add(region)
                    await session.flush()
                region_id = region.id

            vuz = (
                await session.execute(
                    select(m.University).where(m.University.slug == about.slug)
                )
            ).scalar_one_or_none()
            if vuz is None:
                vuz = m.University(slug=about.slug, short_name="", full_name="")
                session.add(vuz)
            vuz.short_name = about.short_name
            vuz.full_name = about.full_name
            vuz.region_id = region_id
            vuz.is_state = about.is_state
            vuz.is_branch = about.is_branch
            vuz.category = about.category
            vuz.avg_score = about.avg_score
            vuz.budget_seats = about.budget_seats
            if dorm is not None:
                vuz.dorm = dorm.dorm
                vuz.dorm_rating = dorm.dorm_rating
            vuz.is_active = True
            vuz.scraped_at = now
            await session.flush()

            # дни открытых дверей: заменяем целиком (сайт отдаёт только предстоящие)
            await session.execute(delete(m.OpenDay).where(m.OpenDay.university_id == vuz.id))
            for day in open_days:
                session.add(
                    m.OpenDay(
                        university_id=vuz.id,
                        starts_at=day.starts_at,
                        title=day.title,
                        location=day.location,
                        scraped_at=now,
                    )
                )

            faculty_ids: dict[str, int] = {}
            existing_fac = (
                (
                    await session.execute(
                        select(m.Faculty).where(m.Faculty.university_id == vuz.id)
                    )
                )
                .scalars()
                .all()
            )
            faculty_ids = {f.name: f.id for f in existing_fac}
            for name in about.faculties:
                if name not in faculty_ids:
                    fac = m.Faculty(university_id=vuz.id, name=name)
                    session.add(fac)
                    await session.flush()
                    faculty_ids[name] = fac.id

            # справочники УГСН/направлений пополняются от каждого вуза;
            # заодно пишем полный перечень направлений вуза (university_direction)
            code_to_dir: dict[str, int] = {}
            about_direction_ids: set[int] = set()
            for ref in about.directions:
                ugsn_code = ref.code[:2] + ".00.00"
                ugsn = await session.get(m.Ugsn, ugsn_code)
                if ugsn is None:
                    session.add(
                        m.Ugsn(code=ugsn_code, name=about.ugsn_names.get(ugsn_code, ugsn_code))
                    )
                elif ugsn.name == ugsn.code and about.ugsn_names.get(ugsn_code):
                    ugsn.name = about.ugsn_names[ugsn_code]

                direction = (
                    await session.execute(
                        select(m.Direction).where(m.Direction.code == ref.code)
                    )
                ).scalar_one_or_none()
                if direction is None:
                    direction = m.Direction(
                        id=ref.np_id,
                        code=ref.code,
                        name=ref.name,
                        level=ref.level,
                        ugsn_code=ugsn_code,
                    )
                    session.add(direction)
                    await session.flush()
                code_to_dir[ref.code] = direction.id
                about_direction_ids.add(direction.id)

                if await session.get(m.UniversityDirection, (vuz.id, direction.id)) is None:
                    session.add(
                        m.UniversityDirection(
                            university_id=vuz.id, direction_id=direction.id, scraped_at=now
                        )
                    )
                else:
                    await session.execute(
                        update(m.UniversityDirection)
                        .where(
                            m.UniversityDirection.university_id == vuz.id,
                            m.UniversityDirection.direction_id == direction.id,
                        )
                        .values(scraped_at=now)
                    )

            # направления, исчезнувшие со страницы /about, отвязываем от вуза
            await session.execute(
                delete(m.UniversityDirection).where(
                    m.UniversityDirection.university_id == vuz.id,
                    m.UniversityDirection.direction_id.not_in(about_direction_ids or {-1}),
                )
            )

            seen_program_ids: set[int] = set()
            for summary in programs:
                direction_id = code_to_dir.get(summary.direction_code)
                if direction_id is None:
                    known = (
                        await session.execute(
                            select(m.Direction).where(m.Direction.code == summary.direction_code)
                        )
                    ).scalar_one_or_none()
                    if known is None:
                        log.warning(
                            "%s: направление %s не найдено, программа %s пропущена",
                            about.slug,
                            summary.direction_code,
                            summary.id,
                        )
                        continue
                    direction_id = known.id

                seen_program_ids.add(summary.id)
                program = await session.get(m.Program, summary.id)
                if program is None:
                    program = m.Program(id=summary.id, university_id=vuz.id, direction_id=direction_id)
                    session.add(program)
                program.university_id = vuz.id
                program.direction_id = direction_id
                program.faculty_id = faculty_ids.get(summary.faculty or "")
                program.profile = summary.profile
                program.is_active = True
                program.scraped_at = now

                for ps in summary.pass_scores:
                    form_row = await session.get(m.ProgramForm, (summary.id, ps.form))
                    if form_row is None:
                        form_row = m.ProgramForm(program_id=summary.id, form=ps.form)
                        session.add(form_row)
                    await self._log_change(
                        session, "program_form", summary.id, "pass_score",
                        form_row.pass_score, ps.score, run_id,
                    )
                    form_row.pass_score = ps.score
                    form_row.pass_score_year = ps.year
                if summary.paid_only and not summary.pass_scores:
                    form_row = await session.get(m.ProgramForm, (summary.id, "full"))
                    if form_row is None:
                        session.add(
                            m.ProgramForm(program_id=summary.id, form="full", paid_only=True)
                        )

                existing_exams = (
                    (
                        await session.execute(
                            select(m.ProgramExam).where(m.ProgramExam.program_id == summary.id)
                        )
                    )
                    .scalars()
                    .all()
                )
                wanted = {
                    (await self._subject_id(session, s), kind)
                    for kind, subjects in (
                        ("required", summary.exams.required),
                        ("choice", summary.exams.choice),
                    )
                    for s in subjects
                }
                current = {(e.subject_id, e.kind) for e in existing_exams}
                for exam in existing_exams:
                    if (exam.subject_id, exam.kind) not in wanted:
                        await session.delete(exam)
                for subject_id, kind in wanted - current:
                    session.add(
                        m.ProgramExam(program_id=summary.id, subject_id=subject_id, kind=kind)
                    )

            # исчезнувшие со страницы программы вуза деактивируем (не удаляем)
            if programs:
                stale = (
                    (
                        await session.execute(
                            select(m.Program).where(
                                m.Program.university_id == vuz.id,
                                m.Program.id.not_in(seen_program_ids),
                                m.Program.is_active,
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                for program in stale:
                    program.is_active = False

            await session.commit()

    # ---------- обходы ----------

    async def _crawl_vuz_with_about(self, slug: str, about: VuzAbout, run_id: int) -> tuple[int, int]:
        """Глубокий обход вуза при уже загруженном /about: общежитие, ДОД и полный
        список профилей по каждому направлению (/proxodnoi?{np_id})."""
        dorm = parse_vuz_obsh(await self.client.get(f"/vuzu/{slug}/obsh"))
        open_days = parse_vuz_dod(await self.client.get(f"/vuzu/{slug}/dod"))

        programs: list[ProgramSummary] = []
        for ref in about.directions:
            html = await self.client.get(f"/vuzu/{slug}/proxodnoi?{ref.np_id}")
            programs.extend(parse_program_cards(html))

        await self._upsert_vuz(about, dorm, programs, open_days, run_id)
        return len(programs), len(about.directions)

    async def _crawl_vuz(self, slug: str, run_id: int) -> tuple[int, int]:
        about = parse_vuz_about(await self.client.get(f"/vuzu/{slug}/about"), slug)
        return await self._crawl_vuz_with_about(slug, about, run_id)

    async def run_region(self, region_query: str) -> int:
        """Надёжный обход региона: скан всех вузов из sitemap, фильтр по региону
        со страницы /about, глубокий обход только совпавших."""
        run_id = await self._start_run("region")
        ok = failed = skipped = 0
        needle = region_query.lower()
        try:
            index = parse_sitemap(await self.client.get("/map/sitemap.php"))
            log.info(
                "обход региона «%s»: проверяю %d вузов из sitemap", region_query, len(index.vuz_slugs)
            )
            for slug in index.vuz_slugs:
                try:
                    about = parse_vuz_about(await self.client.get(f"/vuzu/{slug}/about"), slug)
                    if needle not in (about.region_name or "").lower():
                        skipped += 1
                        continue
                    n_prog, n_dir = await self._crawl_vuz_with_about(slug, about, run_id)
                    ok += 1
                    log.info(
                        "[%d] %s (%s): %d направлений, %d профилей",
                        ok, slug, about.short_name, n_dir, n_prog,
                    )
                except (ValidationError, Exception):  # noqa: BLE001
                    failed += 1
                    log.exception("вуз %s пропущен", slug)
        finally:
            await self._finish_run(run_id, ok, failed)
        log.info(
            "регион «%s»: обойдено %d, пропущено (другой регион) %d, ошибок %d",
            region_query, ok, skipped, failed,
        )
        return run_id

    async def run_light(self, limit_vuz: int | None = None, slugs: list[str] | None = None) -> int:
        """Полный обход вузов: about + общежитие + ДОД + все профили по направлениям.

        Если slugs не задан — обходим все вузы из sitemap (с учётом limit_vuz).
        """
        run_id = await self._start_run("light")
        ok = failed = 0
        try:
            if slugs is None:
                index = parse_sitemap(await self.client.get("/map/sitemap.php"))
                slugs = index.vuz_slugs[:limit_vuz] if limit_vuz else index.vuz_slugs
            log.info("light-обход: %d вузов", len(slugs))
            for i, slug in enumerate(slugs, 1):
                try:
                    n_prog, n_dir = await self._crawl_vuz(slug, run_id)
                    ok += 1
                    log.info(
                        "[%d/%d] %s: %d направлений, %d профилей", i, len(slugs), slug, n_dir, n_prog
                    )
                except (ValidationError, Exception) as exc:  # noqa: BLE001
                    failed += 1
                    log.exception("вуз %s пропущен: %s", slug, exc)
        finally:
            await self._finish_run(run_id, ok, failed)
        return run_id

    async def run_np(self, limit: int | None = None) -> int:
        """Агрегаты направлений по России (мин/средний балл)."""
        run_id = await self._start_run("np")
        ok = failed = 0
        try:
            index = parse_sitemap(await self.client.get("/map/sitemap.php"))
            np_ids = index.np_ids[:limit] if limit else index.np_ids
            for np_id in np_ids:
                try:
                    aggregates = parse_np_page(await self.client.get(f"/np/{np_id}/"), np_id)
                    async with session_factory() as session:
                        direction = await session.get(m.Direction, np_id)
                        if direction is not None:
                            direction.min_score = aggregates.min_score
                            direction.avg_score = aggregates.avg_score
                            direction.scraped_at = datetime.now()
                            await session.commit()
                    ok += 1
                except Exception:  # noqa: BLE001
                    failed += 1
                    log.exception("направление %s пропущено", np_id)
        finally:
            await self._finish_run(run_id, ok, failed)
        return run_id

    async def run_full(self, limit: int | None = None) -> int:
        """Карточки программ: стоимость, места, квоты. Самый долгий обход."""
        run_id = await self._start_run("full")
        ok = failed = 0
        try:
            async with session_factory() as session:
                ids = (
                    (
                        await session.execute(
                            select(m.Program.id)
                            .where(m.Program.is_active)
                            .order_by(m.Program.detailed_at.is_(None).desc(), m.Program.detailed_at)
                        )
                    )
                    .scalars()
                    .all()
                )
            if limit:
                ids = ids[:limit]
            log.info("full-обход: %d карточек программ", len(ids))
            for i, program_id in enumerate(ids, 1):
                try:
                    card = parse_program_card(
                        await self.client.get(f"/program/n?{program_id}"), program_id
                    )
                    async with session_factory() as session:
                        program = await session.get(m.Program, program_id)
                        if program is None:
                            continue
                        for form_info in card.forms:
                            row = await session.get(
                                m.ProgramForm, (program_id, form_info.form)
                            )
                            if row is None:
                                row = m.ProgramForm(program_id=program_id, form=form_info.form)
                                session.add(row)
                            await self._log_change(
                                session, "program_form", program_id, "tuition",
                                row.tuition, form_info.tuition, run_id,
                            )
                            row.pass_score = form_info.pass_score or row.pass_score
                            row.pass_score_year = form_info.pass_score_year or row.pass_score_year
                            row.pass_score_delta = form_info.pass_score_delta
                            row.budget_seats = form_info.budget_seats
                            row.seats_main = form_info.seats_main
                            row.seats_quota = form_info.seats_quota
                            row.avg_enrolled_score = form_info.avg_enrolled_score
                            row.tuition = form_info.tuition
                            row.paid_only = form_info.paid_only
                        program.detailed_at = datetime.now()
                        await session.commit()
                    ok += 1
                    if i % 500 == 0:
                        log.info("[%d/%d] карточек обработано", i, len(ids))
                except Exception:  # noqa: BLE001
                    failed += 1
                    log.exception("карточка %s пропущена", program_id)
        finally:
            await self._finish_run(run_id, ok, failed)
        return run_id
