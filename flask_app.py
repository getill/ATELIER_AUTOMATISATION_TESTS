# pyrefly: ignore [missing-import]
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import time
import datetime
from storage import init_db, save_run, list_runs, get_latest_run, get_run_by_id, get_db_connection
from tester.runner import run_all_tests

app = Flask(__name__)
app.secret_key = "atelier_automatisation_tests_secret_key" # Required for Flask flash messages session context

# Initialize database schema
init_db()

@app.route("/")
def index():
    """Redirect home route to the dashboard page."""
    return redirect(url_for("dashboard"))


@app.route("/consignes")
def consignes():
    """Serve original exercise instructions sheet for reference."""
    return render_template("consignes.html")


@app.route("/dashboard")
def dashboard():
    """Serve the premium dark mode analytics and artwork visualizer dashboard."""
    latest_run = get_latest_run()
    # Pull the last 15 runs to plot in trend sparklines & charts
    history = list_runs(15)
    
    return render_template(
        "dashboard.html",
        latest_run=latest_run,
        history=history,
        now=datetime.datetime.now().isoformat()
    )


@app.route("/run", methods=["GET", "POST"])
def run_tests():
    """
    Triggers a live execution of the testing suite.
    Includes an anti-spam cooldown lock to limit execution to once every 10 seconds.
    """
    latest = get_latest_run()
    if latest:
        try:
            # Enforce 10s cooldown
            latest_time = datetime.datetime.fromisoformat(latest["timestamp"])
            now = datetime.datetime.now().astimezone()
            delta = (now - latest_time).total_seconds()
            
            if delta < 10:
                flash(
                    f"Anti-Spam : Veuillez patienter {int(10 - delta)}s avant de relancer un test.", 
                    "warning"
                )
                return redirect(url_for("dashboard"))
        except Exception:
            pass  # Fallback if timestamp parsing hits any edge case

    try:
        # Run test cases & gather QoS metrics
        run_data = run_all_tests()
        run_id = save_run(run_data)
        
        passed = run_data["summary"]["passed"]
        failed = run_data["summary"]["failed"]
        
        if failed == 0:
            flash(
                f"Run #{run_id} terminé avec succès ! 100% des tests validés ({passed}/{passed}).", 
                "success"
            )
        else:
            flash(
                f"Run #{run_id} terminé avec {failed} anomalie(s). Couverture : {passed} validés, {failed} échoués.", 
                "danger"
            )
            
    except Exception as e:
        flash(f"Erreur d'exécution de la suite de tests : {str(e)}", "danger")
        
    return redirect(url_for("dashboard"))


@app.route("/health")
def health():
    """
    JSON status check endpoint verifying database connectivity and sharing QoS stats.
    Satisfies task health bonus.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM runs")
        runs_count = cursor.fetchone()[0]
        conn.close()
        
        latest = get_latest_run()
        latest_summary = None
        if latest:
            latest_summary = {
                "id": latest["id"],
                "timestamp": latest["timestamp"],
                "passed": latest["passed"],
                "failed": latest["failed"],
                "error_rate": latest["error_rate"],
                "latency_avg_ms": latest["latency_avg"],
                "latency_p95_ms": latest["latency_p95"],
                "availability": latest["availability"]
            }
            
        return jsonify({
            "status": "healthy",
            "api_tested": "Art Institute of Chicago API (v1)",
            "database": {
                "status": "connected",
                "total_runs_stored": runs_count
            },
            "latest_run": latest_summary
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


@app.route("/export/json")
def export_json():
    """
    Generates a full history downloadable JSON export.
    Satisfies export JSON bonus.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM runs ORDER BY id DESC")
        run_ids = [row["id"] for row in cursor.fetchall()]
        conn.close()
        
        all_runs = []
        for rid in run_ids:
            run_detail = get_run_by_id(rid)
            if run_detail:
                all_runs.append(run_detail)
                
        response = jsonify(all_runs)
        response.headers["Content-Disposition"] = "attachment; filename=api_test_runs_history.json"
        return response
    except Exception as e:
        return jsonify({"error": f"Failed to compile history dump: {str(e)}"}), 500


if __name__ == "__main__":
    # Local runtime configuration
    app.run(host="0.0.0.0", port=5000, debug=True)
