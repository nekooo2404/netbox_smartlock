import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("check-sso-preflight.py")


BASE_ENV = """\
REMOTE_AUTH_ENABLED=True
REMOTE_AUTH_AUTO_CREATE_USER=True
REMOTE_AUTH_BACKEND=social_core.backends.google.GoogleOAuth2
REMOTE_AUTH_DEFAULT_GROUPS=Guest
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=client-id.apps.googleusercontent.com
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE=openid email profile
SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_VERIFIED_EMAIL=True
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS=prompt=select_account
CSRF_TRUSTED_ORIGINS=http://localhost:8000
LOGOUT_REDIRECT_URL=http://localhost:8000/login/
REDIS_PASSWORD=redis-secret
REDIS_CACHE_PASSWORD=redis-cache-secret
"""


class SsoPreflightTest(unittest.TestCase):
    def run_preflight(self, env_text, *args, redis_password="redis-secret", redis_cache_password="redis-cache-secret"):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp_dir:
            temp_path = Path(temp_dir)
            env_file = temp_path / "netbox.env"
            env_file.write_text(env_text, encoding="utf-8")
            redis_env_file = temp_path / "redis.env"
            redis_env_file.write_text(f"REDIS_PASSWORD={redis_password}\n", encoding="utf-8")
            redis_cache_env_file = temp_path / "redis-cache.env"
            redis_cache_env_file.write_text(f"REDIS_PASSWORD={redis_cache_password}\n", encoding="utf-8")
            secret_file = temp_path / "secrets" / "google_oauth2_secret.txt"
            secret_file.parent.mkdir()
            secret_file.write_text("realistic-google-secret", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--env-file",
                    str(env_file.relative_to(Path(__file__).parent)),
                    "--redis-env-file",
                    str(redis_env_file.relative_to(Path(__file__).parent)),
                    "--redis-cache-env-file",
                    str(redis_cache_env_file.relative_to(Path(__file__).parent)),
                    "--secrets-dir",
                    str(secret_file.parent.relative_to(Path(__file__).parent)),
                    *args,
                ],
                cwd=Path(__file__).parent,
                text=True,
                capture_output=True,
                check=False,
            )
        return result

    def test_missing_openid_scope_fails(self):
        result = self.run_preflight(BASE_ENV.replace("openid email profile", "email profile"))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("openid email profile", result.stdout)

    def test_secret_in_env_fails(self):
        result = self.run_preflight(BASE_ENV + "SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=bad\n")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Remove SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", result.stdout)

    def test_unescaped_secret_key_dollar_fails(self):
        result = self.run_preflight(BASE_ENV + "SECRET_KEY=abc$broken\n")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unescaped '$'", result.stdout)

    def test_wrong_callback_fails(self):
        result = self.run_preflight(BASE_ENV.replace("http://localhost:8000", "http://127.0.0.1:8000"))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing callback", result.stdout)

    def test_redis_password_drift_fails(self):
        result = self.run_preflight(BASE_ENV, redis_password="different")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("REDIS_PASSWORD in netbox.env must match", result.stdout)

    def test_redis_cache_password_drift_fails(self):
        result = self.run_preflight(BASE_ENV, redis_cache_password="different")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("REDIS_CACHE_PASSWORD in netbox.env must match", result.stdout)

    def test_utf8_bom_env_file_is_supported(self):
        result = self.run_preflight("\ufeff# Google: http://localhost:8000/oauth/complete/google-oauth2/\n" + BASE_ENV)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_production_rejects_localhost_and_insecure_settings(self):
        result = self.run_preflight(BASE_ENV, "--production", "--base-url", "http://localhost:8000")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("https://", result.stdout)
        self.assertIn("SECURE_SSL_REDIRECT", result.stdout)

    def test_production_accepts_https_domain_hardening(self):
        env_text = BASE_ENV.replace("http://localhost:8000", "https://netbox.example.com") + """\
# Google: https://netbox.example.com/oauth/complete/google-oauth2/
SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS=company.com
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SAMESITE=Lax
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
"""
        result = self.run_preflight(env_text, "--production", "--base-url", "https://netbox.example.com")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
