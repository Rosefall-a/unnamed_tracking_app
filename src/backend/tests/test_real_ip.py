from src.core.env_handler import EnvConfigHandler
from src.core.real_ip import DEFAULT_REAL_IP_HEADER,DEFAULT_TRUSTED_PROXIES,get_effective_real_ip_config,get_real_ip_presets,validate_real_ip_header,validate_trusted_proxies

def test_default_real_ip_config_is_loopback_only():
    c=get_effective_real_ip_config(EnvConfigHandler({}),None,None)
    assert c["header"]==DEFAULT_REAL_IP_HEADER
    assert c["trusted_proxies"]==" ".join(DEFAULT_TRUSTED_PROXIES)

def test_persisted_real_ip_config():
    c=get_effective_real_ip_config(EnvConfigHandler({}),"CF-Connecting-IP","127.0.0.1/32 100.64.0.0/10")
    assert c["header"]=="CF-Connecting-IP" and c["trusted_proxies"]=="127.0.0.1/32 100.64.0.0/10"

def test_environment_overrides_persisted():
    h=EnvConfigHandler({"NGINX_REALIP_HEADER":"X-Forwarded-For","NGINX_REALIP_TRUSTED_PROXIES":"10.0.0.0/8"})
    assert get_effective_real_ip_config(h,"CF-Connecting-IP","127.0.0.1/32")["trusted_proxies"]=="10.0.0.0/8"

def test_presets_are_backend_owned():
    p=get_real_ip_presets()
    assert {"local","cgnat","cloudflare"}==set(p)
    assert "100.64.0.0/10" in p["cgnat"]["values"]

def test_invalid_values():
    try: validate_real_ip_header("bad;include /tmp/evil;"); assert False
    except ValueError: pass
    try: validate_trusted_proxies("10.0.0.0/8;include /tmp/evil;"); assert False
    except ValueError: pass
