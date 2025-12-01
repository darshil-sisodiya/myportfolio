from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import httpx
from typing import List, Dict, Any
import os

app = FastAPI()

# change this to your actual frontend URL in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <- dev: allow everything
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/images", StaticFiles(directory="images"), name="images")

LEETCODE_USERNAME = "user6432"
LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

RECENT_QUERY = """
query recentAcSubmissions($username: String!) {
  recentAcSubmissionList(username: $username) {
    title
    titleSlug
    timestamp
  }
}
"""

STATS_QUERY = """
query userStats($username: String!) {
  matchedUser(username: $username) {
    submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
        submissions
      }
    }
  }
}
"""


# ---------- Serve index.html ----------
@app.get("/")
async def serve_index():
    # index.html must be in the same folder as main.py
    return FileResponse("index.html")
# -------------------------------------

@app.get("/resume")
async def serve_resume():
    return FileResponse("resume.pdf", media_type="application/pdf")

async def fetch_leetcode(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            LEETCODE_GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers={"Content-Type": "application/json"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise RuntimeError(f"LeetCode GraphQL error: {data['errors']}")
        return data["data"]


@app.get("/leetcode/activity")
async def leetcode_activity():
    # fetch recent submissions
    recent_data = await fetch_leetcode(
        RECENT_QUERY, {"username": LEETCODE_USERNAME}
    )
    recent_raw: List[Dict[str, Any]] = recent_data.get(
        "recentAcSubmissionList", []
    )

    # fetch stats
    stats_data = await fetch_leetcode(
        STATS_QUERY, {"username": LEETCODE_USERNAME}
    )
    stats_raw = (
        stats_data.get("matchedUser", {})
        .get("submitStatsGlobal", {})
        .get("acSubmissionNum", [])
    )

    total_solved = 0
    easy = medium = hard = 0
    for item in stats_raw:
        diff = item["difficulty"]
        count = item["count"]
        if diff == "All":
            total_solved = count
        elif diff == "Easy":
            easy = count
        elif diff == "Medium":
            medium = count
        elif diff == "Hard":
            hard = count

    recent = [
        {
            "title": r["title"],
            "titleSlug": r["titleSlug"],
            "timestamp": int(r["timestamp"]),
        }
        for r in recent_raw
    ]

    return {
        "username": LEETCODE_USERNAME,
        "totalSolved": total_solved,
        "easy": easy,
        "medium": medium,
        "hard": hard,
        "recent": recent,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
