import os

import httpx
import streamlit as st

st.set_page_config(page_title="SupportOps AI", page_icon="🔎", layout="wide")
BASE = os.getenv("API_URL", "http://127.0.0.1:8000")


def api(method, path, data=None):
    try:
        res = httpx.request(
            method,
            BASE + path,
            json=data,
            headers={"X-Admin-Key": st.session_state.get("admin_key", "")},
            timeout=600,
        )
        res.raise_for_status()
        return res.json()
    except httpx.HTTPStatusError as exc:
        st.error(f"Request failed ({exc.response.status_code}). {exc.response.text[:200]}")
    except httpx.RequestError:
        st.error("The API could not be reached. Check its address and service status.")
    st.stop()


def show_sources(items):
    for e in items:
        with st.expander(f"{e['title']} · {e['section']}"):
            st.text(e["excerpt"])
            st.caption(f"{e['source_type']} · {e['chunk_id']}")
            if e["url"].startswith(("https://fastapi.tiangolo.com/", "https://github.com/fastapi/fastapi/")):
                st.link_button("Open source", e["url"])


st.sidebar.title("SupportOps AI")
page = st.sidebar.radio(
    "Workspace", ["Overview", "Create ticket", "Investigations", "Knowledge base", "Evaluation"]
)
st.title(page)
if page == "Overview":
    tickets = api("GET", "/v1/tickets")
    docs = api("GET", "/v1/documents")
    for col, label, value in zip(
        st.columns(4),
        ["Tickets", "Needs review", "Escalated", "Sources"],
        [
            len(tickets),
            sum(t["status"] == "NEEDS_REVIEW" for t in tickets),
            sum(t["status"] == "ESCALATED" for t in tickets),
            len(docs),
        ],
        strict=False,
    ):
        col.metric(label, value, border=True)
    st.subheader("Recent tickets")
    if tickets:
        st.table(
            [
                {
                    "Ticket": f"#{t['id']}",
                    "Issue": t["title"],
                    "Status": t["status"].replace("_", " ").title(),
                    "Created (UTC)": t["created"][:16].replace("T", " "),
                }
                for t in tickets[:20]
            ],
            hide_index=True,
        )
    else:
        st.info("Create your first ticket to start an investigation.")
elif page == "Create ticket":
    with st.form("new"):
        title = st.text_input("Issue title", max_chars=300)
        desc = st.text_area("Problem description", max_chars=6000)
        ver = st.text_input("Affected software version", max_chars=100)
        err = st.text_area("Redacted error message", max_chars=2000)
        ctx = st.text_area("Environment and impact", max_chars=1500)
        outage = st.checkbox("Confirmed production outage")
        investigate = st.checkbox("Analyze after creating")
        if st.form_submit_button("Create ticket"):
            t = api(
                "POST",
                "/v1/tickets",
                {
                    "title": title,
                    "description": desc,
                    "version": ver,
                    "error": err,
                    "context": ctx,
                    "impact": "production_outage" if outage else "unspecified",
                },
            )
            st.success(f"Saved ticket #{t['id']}.")
            if investigate:
                api("POST", f"/v1/tickets/{t['id']}/analyze")
                st.success("Draft ready in Investigations.")
elif page == "Investigations":
    tickets = api("GET", "/v1/tickets")
    if not tickets:
        st.info("No tickets yet.")
        st.stop()
    t = st.selectbox("Ticket", tickets, format_func=lambda r: f"#{r['id']} · {r['title']}")
    path = f"/v1/tickets/{t['id']}"
    detail = api("GET", path)
    st.caption(detail["status"])
    st.text(detail["description"])
    for key in ("version", "error", "context"):
        if detail[key]:
            st.text(f"{key.title()} · {detail[key]}")
    if detail["status"] in ("NEW", "NEEDS_REVIEW", "REJECTED", "ESCALATED") and st.button(
        "Run investigation"
    ):
        with st.spinner("Retrieving evidence and drafting a response"):
            api("POST", path + "/analyze")
        st.rerun()
    history = api("GET", path + "/analyses")
    if history:
        a = st.selectbox(
            "Analysis history", history, format_func=lambda r: f"Analysis {r['id']} · {r['created']}"
        )
        d = a["draft"]
        st.subheader(d["summary"])
        st.caption(
            f"{d['category']} · {d['component']} · {a['priority']} priority · {a['provider'] or 'No model call'}"
        )
        if a["escalation"]:
            st.warning(d["escalation_reason"])
        for label, items in [
            ("Possible explanations", d["explanations"]),
            ("Troubleshooting steps", d["steps"]),
        ]:
            if items:
                st.subheader(label)
                for item in items:
                    st.text(item["text"])
                    st.caption(f"Evidence · {item['quote']}")
        if d["missing"]:
            st.subheader("Missing information")
            for item in d["missing"]:
                st.text(item)
        show_sources(a["citations"])
        with st.expander("All retrieved evidence"):
            show = a["retrieved"]
            st.json(show)
        reply = st.text_area("Engineer reply", a["edited_reply"] or d["reply"], key=f"reply{a['id']}")
        if a["id"] == history[0]["id"] and detail["status"] == "NEEDS_REVIEW":
            decision = st.radio("Review decision", ["APPROVED", "REJECTED", "ESCALATED"], horizontal=True)
            if st.button("Save review"):
                api("POST", path + "/review", {"analysis_id": a["id"], "decision": decision, "reply": reply})
                st.rerun()
        elif a["decision"]:
            st.caption(f"Saved decision · {a['decision']}")
        with st.form("feedback"):
            useful = st.checkbox("Useful recommendation")
            relevant = st.checkbox("Relevant evidence")
            accurate = st.checkbox("Accurate steps")
            comments = st.text_input("Reviewer comments")
            if st.form_submit_button("Record feedback"):
                api(
                    "POST",
                    "/v1/feedback",
                    {
                        "ticket_id": t["id"],
                        "analysis_id": a["id"],
                        "useful": useful,
                        "relevant": relevant,
                        "accurate": accurate,
                        "comments": comments,
                    },
                )
                st.success("Feedback saved.")
elif page == "Knowledge base":
    docs = api("GET", "/v1/documents")
    st.subheader("Indexed documents")
    if docs:
        st.dataframe(docs, hide_index=True)
    else:
        st.info("Synchronize a source to build the index.")
    query = st.text_input("Search the knowledge base")
    if query:
        show_sources(api("POST", "/v1/search", {"query": query}))
    with st.expander("Administration"):
        st.text_input("Administrator key", type="password", key="admin_key")
        source = st.selectbox("Source", ["official", "local", "issue"])
        issue = st.number_input("Issue number", min_value=1) if source == "issue" else None
        if st.button("Synchronize"):
            st.json(api("POST", "/v1/ingestion/sync", {"source": source, "issue_number": issue}))
        if st.button("Show synchronization jobs"):
            st.dataframe(api("GET", "/v1/ingestion/jobs"))
        if docs:
            doc = st.selectbox("Document to remove", [d["id"] for d in docs])
            if st.button("Remove selected document"):
                api("DELETE", "/v1/documents/" + doc)
                st.rerun()
else:
    st.text_input("Administrator key", type="password", key="admin_key")
    if st.session_state.get("admin_key"):
        report = (
            api("POST", "/v1/evaluation/run")
            if st.button("Evaluate current index")
            else api("GET", "/v1/evaluation/latest")
        )
        if report["status"] == "not_evaluated":
            st.info("Not evaluated yet.")
        else:
            st.subheader("Retrieval quality")
            st.table(report["summary"])
            st.caption(f"{report['cases']} labeled questions · top {report['k']} results")
            left, right = st.columns(2)
            left.metric(
                "Median retrieval time",
                f"{report['latency_p50_ms']:.1f} ms" if report.get("latency_p50_ms") is not None else "—",
            )
            right.metric("Failed retrievals", report["errors"])
            if "investigations" in report:
                st.subheader("Investigation outcomes")
                st.json(report["investigations"])
            with st.expander("Per-question rankings and corpus revisions"):
                st.json(report)
