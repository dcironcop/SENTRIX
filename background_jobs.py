import threading
import uuid
from concurrent.futures import ThreadPoolExecutor


_executor = ThreadPoolExecutor(max_workers=2)
_jobs = {}
_lock = threading.Lock()


def start_job(func, *args, **kwargs):
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {"status": "queued", "result": None, "error": None}

    def _run():
        with _lock:
            _jobs[job_id]["status"] = "running"
        try:
            result = func(*args, **kwargs)
            with _lock:
                _jobs[job_id]["status"] = "finished"
                _jobs[job_id]["result"] = result
        except Exception as exc:  # noqa: BLE001
            with _lock:
                _jobs[job_id]["status"] = "failed"
                _jobs[job_id]["error"] = str(exc)

    _executor.submit(_run)
    return job_id


def get_job(job_id):
    with _lock:
        return _jobs.get(job_id)
