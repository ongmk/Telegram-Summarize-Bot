import json
import shutil
import socket
import ssl
from datetime import datetime
from urllib.parse import urlparse

import certifi
import requests
from logzero import logger


def get_ssl_certificate(url, raw: bool = True) -> str:
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    port = parsed_url.port or 443  # Use default HTTPS port if not specified

    context = ssl.create_default_context()

    with socket.create_connection((hostname, port)) as sock:
        if raw:
            with context.wrap_socket(sock, server_hostname=hostname) as sslsock:
                sslsock.do_handshake()  # Establish the SSL/TLS handshake
                der_cert = sslsock.getpeercert(binary_form=True)
                certificate = ssl.DER_cert_to_PEM_cert(der_cert)
        else:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                certificate = ssock.getpeercert()

    return certificate


def append_cert_to_cacert(new_cert_content) -> str:
    try:
        # Read the existing cacert.pem file
        filepath = certifi.where()
        with open(filepath, "r", encoding="utf-8") as file:
            cacert_content = file.read()

        if new_cert_content in cacert_content:
            logger.info("Certificate already in cacert.pem file.  No action needed.")

        else:
            # Ensure the new certificate ends with a newline
            if not new_cert_content.endswith("\n"):
                new_cert_content += "\n"

            # Create a backup of the file
            timestamp = datetime.now().strftime(".backup_%Y%m%d_%H%M%S_%f")
            backup_filepath = filepath + timestamp
            shutil.copy2(filepath, backup_filepath)
            logger.info(f"Backup of the original file created: {backup_filepath}")

            # Append the text block to the file
            with open(filepath, "a", encoding="utf-8") as file:
                file.write(new_cert_content)
                logger.info(f"Certificate appended to the {filepath}.")

    except FileNotFoundError:
        logger.error(f"The file {filepath} does not exist.")
        return False
    except IOError as e:
        logger.error(f"An error occurred while reading the file: {e}")
        return False

    return cacert_content


class KeycloakTokenManager:
    def __init__(
        self,
        keycloak_client_id: str,
        keycloak_client_secret: str,
        keycloak_url: str = "iamfw.home-np.oocl.com",
        keycloak_realm: str = "oocl-dev",
    ) -> None:
        # keycloak token related
        self.keycloak_url = keycloak_url
        self.keycloak_realm = keycloak_realm
        self.keycloak_client_id = keycloak_client_id
        self.keycloak_client_secret = keycloak_client_secret
        self._kc_token = None

    def _http_post(self, url, headers, body) -> json:
        try:
            response = requests.post(url, data=body, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
        except Exception as err:
            logger.error(f"An error occurred: {err}")

    def retrieve_token(self) -> None:
        url = f"https://{self.keycloak_url}/auth/realms/{self.keycloak_realm}/protocol/openid-connect/token"

        keycloak_headers = {
            "Request-client": "IAM_PORTAL",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        keycloak_body = {
            "grant_type": "client_credentials",
            "client_id": self.keycloak_client_id,
            "client_secret": self.keycloak_client_secret,
        }
        keycloak_response = self._http_post(url, keycloak_headers, keycloak_body)
        self._kc_token = keycloak_response["access_token"]

    def kc_get_access_token(self) -> str:
        self.retrieve_token()
        return self._kc_token


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()

    llm_gateway_url = os.getenv("LLM_GATEWAY_URL")

    proxy_url = f"{llm_gateway_url}/models/proxy"
    _ = append_cert_to_cacert(get_ssl_certificate(proxy_url))
    token_mgr = KeycloakTokenManager(
        keycloak_client_id=os.getenv("KEYCLOAK_CLIENT_ID"),
        keycloak_client_secret=os.getenv("KEYCLOAK_CLIENT_SECRET"),
    )
    print(token_mgr.kc_get_access_token())
