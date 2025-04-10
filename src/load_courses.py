from .api_client import get_course_listings, get_course_offering_detail
from .db import create_table, insert_many
from .dropdown_items import subj_list

def safe_strip(value):
    return value.strip() if isinstance(value, str) else ""

def parse_course_data(subject_code):
    data = get_course_listings(subject_code)

    subject_data = (
        data.get("ssr_get_courses_resp", {})
            .get("course_search_result", {})
            .get("subjects", {})
            .get("subject", {})
    )

    course_summaries = subject_data.get("course_summaries")

    if not course_summaries:
        print(f"⚠️ No course summaries found for {subject_code}")
        return []

    courses = course_summaries.get("course_summary", [])
    if not isinstance(courses, list):
        courses = [courses]

    rows = []
    term_rows = []

    for c in courses:
        if not c.get("crse_id"):
            continue

        crse_id = c.get("crse_id")
        row = {
            "id": crse_id,
            "subject": c.get("subject"),
            "subject_name": c.get("subject_lov_descr"),
            "catalog_nbr": safe_strip(c.get("catalog_nbr")),
            "title": safe_strip(c.get("course_title_long")),
            "term_code": c.get("ssr_crse_typoff_cd"),
            "term_desc": c.get("ssr_crse_typoff_cd_lov_descr"),
            "effdt": c.get("effdt"),
            "multi_off": c.get("multi_off"),
            "topic_id": c.get("crs_topic_id")
        }
        rows.append(row)

        # Fetch detailed offering info to extract terms
        detail = get_course_offering_detail(crse_id)
        if not detail:
            continue

        terms = (
            detail.get("ssr_get_course_offering_resp", {})
                .get("course_offering_result", {})
                .get("course_offering", {})
                .get("terms_offered", {})
                .get("term_offered", [])
        )

        if isinstance(terms, dict):
            terms = [terms]

        for term in terms:
            term_rows.append({
                "crse_id": crse_id,
                "strm": term.get("strm"),
                "strm_descr": term.get("strm_lov_descr")
            })

    return rows, term_rows

def main():
    create_table("courses", {
        "id": "TEXT PRIMARY KEY",
        "subject": "TEXT",
        "subject_name": "TEXT",
        "catalog_nbr": "TEXT",
        "title": "TEXT",
        "term_code": "TEXT",
        "term_desc": "TEXT",
        "effdt": "TEXT",
        "multi_off": "TEXT",
        "topic_id": "TEXT"
    })

    create_table("course_terms", {
        "crse_id": "TEXT",
        "strm": "TEXT",
        "strm_descr": "TEXT",
        "PRIMARY KEY (crse_id, strm)": ""
    })

    SKIP_PREFIXES = ["INCC_", "INCG_", "INCH_", "INCU_", "INCS_", "K_", "JGER_", "ROBT_", "ZZZ"]

    for subj in subj_list():
        subject_code = subj.split(" - ")[0].strip()

        if any(subject_code.upper().startswith(prefix) for prefix in SKIP_PREFIXES):
            continue

        print(f"📘 Loading courses for subject: {subject_code}")
        course_rows, term_rows = parse_course_data(subject_code)

        if not course_rows:
            print(f"⚠️ No courses found for {subject_code}")
            continue

        inserted_courses = insert_many("courses", course_rows)
        inserted_terms = insert_many("course_terms", term_rows)
        print(f"✅ Inserted {inserted_courses} courses and {inserted_terms} terms for {subject_code}")

if __name__ == "__main__":
    main()