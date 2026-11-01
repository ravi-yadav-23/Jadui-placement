from typing import Any
from app.core.supabase_client import get_supabase_admin_client

class GitHubReviewRepository:
    def save_review(self, user_id: str, owner: str, repo: str, pr_number: int, review: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "user_id": user_id, 
            "repo_owner": owner, 
            "repo_name": repo, 
            "pr_number": pr_number,
            "score": review.get("score", 0), 
            "summary": review.get("summary"),
            "strengths": review.get("strengths", []), 
            "bugs": review.get("bugs", []),
            "security_risks": review.get("security_risks", []), 
            "ideal_code": review.get("ideal_code"),
        }
        resp = get_supabase_admin_client().table("github_pr_reviews").insert(payload).execute()
        return resp.data[0] if resp.data else {}

    def save_repo_analysis(self, user_id: str, owner: str, repo: str, analysis: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "user_id": user_id, 
            "repo_owner": owner, 
            "repo_name": repo,
            "architecture_score": analysis.get("architecture_score", 0),
            "tech_stack": analysis.get("tech_stack", []),
            "summary": analysis.get("summary"),
            "design_patterns": analysis.get("design_patterns", []),
            "technical_debt": analysis.get("technical_debt", []),
        }
        resp = get_supabase_admin_client().table("github_repo_analyses").insert(payload).execute()
        return resp.data[0] if resp.data else {}

repository = GitHubReviewRepository()
