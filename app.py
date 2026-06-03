"""
Dataverse Table Relationship Visualiser — Flask Application.

A local web app that authenticates users via InteractiveBrowserCredential,
retrieves Dataverse solution metadata, and renders an interactive
table-relationship diagram using vis-network.

No secrets, no App Registration, no Docker — just run it locally.
"""

import uuid

from azure.identity import InteractiveBrowserCredential
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import dataverse_api

import os

# ─── App Setup ────────────────────────────────────────────────────────────────

template_dir = os.environ.get("FLASK_TEMPLATE_FOLDER", "templates")
static_dir = os.environ.get("FLASK_STATIC_FOLDER", "static")

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = uuid.uuid4().hex

# Module-level credential — reused across requests so the user only
# logs in once (the token is cached automatically by azure-identity).
_credential = None
_access_token = None


def _get_credential():
    """Return the shared InteractiveBrowserCredential instance."""
    global _credential
    if _credential is None:
        _credential = InteractiveBrowserCredential()
    return _credential


def _get_token(instance_url: str) -> str:
    """
    Acquire an access token for the given Dataverse instance.

    Uses the cached credential — the browser popup only appears on
    the first call (or when the cached token expires).
    """
    global _access_token
    credential = _get_credential()
    scope = f"{instance_url}.default"
    token = credential.get_token(scope)
    _access_token = token.token
    return _access_token


# ─── Routes ───────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Landing page — enter the Dataverse instance URL."""
    return render_template("index.html")


@app.route("/connect", methods=["POST"])
def connect():
    """
    Store the user's instance URL, authenticate via InteractiveBrowserCredential,
    and redirect to the solutions page.
    """
    instance_url = request.form.get("instance_url", "").strip()
    if not instance_url:
        flash("Please enter a valid Dataverse instance URL.", "error")
        return redirect(url_for("index"))

    # Normalise the URL
    if not instance_url.startswith("https://"):
        instance_url = "https://" + instance_url
    if not instance_url.endswith("/"):
        instance_url += "/"

    session["instance_url"] = instance_url

    try:
        _get_token(instance_url)
    except Exception as e:
        flash(f"Authentication failed: {e}", "error")
        return redirect(url_for("index"))

    return redirect(url_for("solutions"))


@app.route("/solutions")
def solutions():
    """Fetch and display all solutions in the environment."""
    instance_url = session.get("instance_url")

    if not instance_url or not _access_token:
        flash("Please connect to a Dataverse environment first.", "error")
        return redirect(url_for("index"))

    try:
        # Refresh token if needed (silently, no popup if cached)
        token = _get_token(instance_url)
        sols = dataverse_api.get_solutions(instance_url, token)
    except Exception as e:
        flash(f"Failed to retrieve solutions: {e}", "error")
        return redirect(url_for("index"))

    return render_template("solutions.html", solutions=sols, instance_url=instance_url)


@app.route("/diagram/<solution_id>")
def diagram(solution_id):
    """Render the diagram page for a specific solution."""
    instance_url = session.get("instance_url")

    if not instance_url or not _access_token:
        flash("Please connect to a Dataverse environment first.", "error")
        return redirect(url_for("index"))

    solution_name = request.args.get("name", "Solution")

    return render_template(
        "diagram.html",
        solution_id=solution_id,
        solution_name=solution_name,
    )


@app.route("/api/diagram/<solution_id>")
def api_diagram(solution_id):
    """
    JSON API — returns nodes and edges for the vis-network diagram.
    Called asynchronously by the frontend.
    """
    instance_url = session.get("instance_url")

    if not instance_url or not _access_token:
        return jsonify({"error": "Not authenticated"}), 401

    try:
        token = _get_token(instance_url)
        data = dataverse_api.build_diagram_data(instance_url, token, solution_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/table/<logical_name>")
def api_table_details(logical_name):
    """
    JSON API — returns detailed attributes for a single table.
    """
    instance_url = session.get("instance_url")

    if not instance_url or not _access_token:
        return jsonify({"error": "Not authenticated"}), 401

    try:
        token = _get_token(instance_url)
        data = dataverse_api.get_table_details(instance_url, token, logical_name)
        if not data:
            return jsonify({"error": "Table not found"}), 404
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/logout")
def logout():
    """Clear session and reset credential."""
    global _credential, _access_token
    _credential = None
    _access_token = None
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("index"))


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
