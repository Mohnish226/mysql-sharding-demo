import argparse
import json
import logging
import random
import string
import time
from typing import Any, Dict, Optional

import requests


class ShardedUserClient:

    def __init__(self, base_url: str = "http://localhost:8000"):

        self.base_url = base_url
        self.session = requests.Session()
        self._setup_session()

        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def _setup_session(self):
        """Configure the requests session"""
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )
        self.session.timeout = 5

    def _generate_test_data(self, prefix: str = "user") -> Dict[str, str]:
        """Generate random test user data"""
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return {"username": f"{prefix}_{suffix}", "email": f"{suffix}@example.com"}

    def create_user(
        self, username: Optional[str] = None, email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new user with automatic sharding.

        Args:
            username: Optional username (auto-generated if not provided)
            email: Optional email (auto-generated if not provided)

        Returns:
            Dictionary containing user data or error information
        """
        user_data = self._generate_test_data()
        if username:
            user_data["username"] = username
        if email:
            user_data["email"] = email

        try:
            self.logger.info(
                f"Sending create request for username: {user_data['username']}"
            )

            # Send username in the JSON body for sharding
            response = self.session.post(f"{self.base_url}/users", json=user_data)

            # Check if we got a successful response
            if response.status_code == 201 or response.status_code == 200:
                self.logger.info(f"Created user {user_data['username']}")
                return response.json()
            else:
                # Try to get detailed error information
                error_detail = "Unknown error"
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", str(error_data))
                except:
                    error_detail = response.text or f"HTTP {response.status_code}"

                self.logger.error(
                    f"Failed to create user - Status code: {response.status_code}, Error: {error_detail}"
                )

                return {
                    "error": f"{response.status_code} - {error_detail}",
                    "username": user_data["username"],
                }

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request exception while creating user: {str(e)}")
            return {"error": str(e), "username": user_data["username"]}

    def get_user(self, username: str) -> Dict[str, Any]:
        """
        Get user details by username with automatic shard routing.

        Args:
            username: Username to lookup

        Returns:
            Dictionary containing user data or error information
        """
        if not username:
            self.logger.error("Cannot get user: username is empty or None")
            return {"error": "Invalid username"}

        try:
            self.logger.info(f"Getting user with username: {username}")

            # Pass the username in the path only, not as query parameter
            response = self.session.get(f"{self.base_url}/users/{username}")

            if response.status_code == 200:
                self.logger.info(f"Retrieved user {username}")
                return response.json()
            else:
                error_detail = "Unknown error"
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", str(error_data))
                except:
                    error_detail = response.text or f"HTTP {response.status_code}"

                self.logger.error(f"Failed to get user {username}: {error_detail}")
                return {
                    "error": f"{response.status_code} - {error_detail}",
                    "username": username,
                }
        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Request exception while getting user {username}: {str(e)}"
            )
            return {"error": str(e), "username": username}

    def health_check(self) -> bool:
        """Check if the service is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def run_demo(self, num_users: int = 10):
        """Run a demonstration of the sharded system"""
        
        # Wait for service to be ready
        self.logger.info("Waiting for service to be ready...")
        retries = 0
        max_retries = 10

        while not self.health_check() and retries < max_retries:
            time.sleep(1)
            retries += 1
            self.logger.info(f"Waiting for service... ({retries}/{max_retries})")

        if retries >= max_retries:
            self.logger.error("Service did not become ready in time. Aborting demo.")
            return

        self.logger.info("Service is ready!")

        # Create test users
        created_users = []
        for i in range(num_users):
            result = self.create_user()
            # Always append result to track both successes and failures
            created_users.append(result)
            if "error" not in result:
                self.logger.info(
                    f"Created user {i+1}/{num_users}: {result['username']}"
                )
            else:
                self.logger.warning(
                    f"Failed to create user {i+1}/{num_users}: {result.get('username', 'unknown')}"
                )

        # Verify retrieval
        retrieval_errors = 0
        for user in created_users:
            # Use username from either successful creation or from error data
            username = user.get("username")
            if username:
                retrieved = self.get_user(username)
                if "error" in retrieved:
                    retrieval_errors += 1
            else:
                self.logger.error(f"Cannot retrieve user, missing username: {user}")
                retrieval_errors += 1

        # Print summary
        self.logger.info("\nDemo Summary:")
        successful_creations = sum(1 for user in created_users if "error" not in user)
        self.logger.info(f"Total users created: {successful_creations}/{num_users}")
        self.logger.info(f"Retrieval errors: {retrieval_errors}")
        if successful_creations > 0:
            self.logger.info(
                f"Success rate: {(successful_creations - retrieval_errors)/successful_creations:.1%}"
            )
        else:
            self.logger.info("Success rate: 0% (no users were created successfully)")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Test client for sharded user service")
    parser.add_argument(
        "--url", default="http://localhost:8000", help="Base URL for the service"
    )
    parser.add_argument(
        "--users", type=int, default=10, help="Number of test users to create"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)

    client = ShardedUserClient(base_url=args.url)

    print("Creating test user...")
    user = client.create_user()
    print(f"Created user: {json.dumps(user, indent=2)}")

    if "error" not in user:
        print("\nRetrieving user...")
        username = user["username"]
        retrieved = client.get_user(username)
        print(f"Retrieved user: {json.dumps(retrieved, indent=2)}")
    else:
        username = user.get("username", "unknown")
        print(f"\nSkipping retrieval for failed user creation: {username}")

    print("\nRunning demo with multiple users...")
    client.run_demo(args.users)
