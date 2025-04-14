# -*- coding: utf-8 -*-

########################################################################
# This sharding module helps in distributing data across multiple shards
# using a consistent hashing mechanism.
# It uses the MD5 hashing algorithm to generate a hash from the shard key
# and determines the shard number based on the total number of shards.
# This is useful in scenarios where you want to evenly distribute data
# across multiple databases or storage systems.
#
# Example:
#     shard_key = "user123"
#     total_shards = 4
#     shard_number = get_shard_number(shard_key, total_shards)
#     print(shard_number)  # Output: 2
########################################################################

import argparse
import hashlib
import logging
import sys
from random import randint
from typing import Optional, Union


def get_shard_number(
    shard_key: Union[str, int], total_shards: int = 2, logger: logging.Logger = None
) -> int:
    """Determine shard number based on shard key

    Args:
        shard_key: The key used for sharding (will be converted to string if not already)
        total_shards: Total number of available shards (default: 2)
        custom_logger: Optional custom logger to use instead of module logger

    Returns:
        Shard number (1 to total_shards)

    Raises:
        ValueError: If total_shards is not a positive integer
    """

    log = logger or logging.getLogger(__name__)

    # Log input parameters
    log.debug(f"Sharding request: key={shard_key!r}, total_shards={total_shards}")

    # Check if shard_key is None or empty
    if shard_key is None or (isinstance(shard_key, str) and not shard_key.strip()):
        log.error("Shard key is None or empty")
        raise ValueError("Shard key cannot be None or empty")

    if not isinstance(shard_key, str):
        log.info(
            f"Converting non-string shard key {type(shard_key).__name__}({shard_key!r}) to string"
        )
        shard_key = str(shard_key)

    # Check if total_shards is a positive integer
    if not isinstance(total_shards, int) or total_shards <= 0:
        log.error(f"Invalid total_shards value: {total_shards!r}")
        raise ValueError("Total shards must be a positive integer")

    # Early return for single shard
    if total_shards == 1:
        log.debug("Only one shard configured, returning shard 1")
        return 1

    # Generate hash and determine shard
    hashlibkey = hashlib.md5(shard_key.encode()).hexdigest()
    log.debug(f"Generated MD5 hash for '{shard_key}': {hashlibkey}")

    # Convert the hash to an integer and map it to the range of available shards
    hash_int = int(hashlibkey, 16)
    log.debug(f"Converted hash to integer: {hash_int}")

    # Map the hash to a shard number
    shard_number = hash_int % total_shards + 1
    log.debug(f"Mapped key '{shard_key}' to shard {shard_number}/{total_shards}")

    return shard_number


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Test sharding distribution across users and shards"
    )
    parser.add_argument(
        "--users",
        "-u",
        type=int,
        default=0,
        help="Number of test users (default: random between 10-100)",
    )
    parser.add_argument(
        "--shards",
        "-s",
        type=int,
        default=0,
        help="Number of shards (default: random between 2-10)",
    )
    parser.add_argument(
        "--prefix",
        "-p",
        type=str,
        default="user",
        help="Prefix for generated user IDs (default: 'user')",
    )
    args = parser.parse_args()

    logger = logging.getLogger(__name__)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.handlers[0].setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    users = args.users if args.users > 0 else randint(10, 100)
    shards = args.shards if args.shards > 0 else randint(2, 10)

    users = [args.prefix + str(i) for i in range(1, users + 1)]

    results = {}
    for user in users:
        shard_number = get_shard_number(user, shards, logger)
        results[user] = shard_number
        logger.debug(f"User ({user}) → Shard ({shard_number})")

    # Lets see the distribution statistics
    distribution = {}
    print("\nShard distribution statistics:")
    print("--------------------------------")
    print(f"Total users:\t\t {len(users)}")
    print(f"Total shards:\t\t {shards}")
    print(f"Users per shard:\t {len(users) // shards}")
    print(f"Users per shard (max):\t {len(users) // shards + 1}")
    print(f"Users per shard (min):\t {len(users) // shards}")
    print(f"Users per shard (avg):\t {len(users) / shards:.1f}")
    print("\nShard\tUsers\tPercentage")
    print("--------------------------------")
    for shard in range(1, shards + 1):
        count = list(results.values()).count(shard)
        distribution[shard] = count
        percentage = count / len(users) * 100
        print(f"{shard}\t{count}\t{percentage:.1f}%")
