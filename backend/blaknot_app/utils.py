def client_ip(request):
    """IP клиента, согласованный с DRF NUM_PROXIES=1: берём последний адрес X-Forwarded-For,
    который дописал/выставил наш единственный доверенный прокси (nginx или фронт).
    Бэкенд не публикуется в интернет, поэтому подделать этот заголовок снаружи нельзя."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    parts = [p.strip() for p in xff.split(",") if p.strip()]
    return parts[-1] if parts else request.META.get("REMOTE_ADDR", "")
