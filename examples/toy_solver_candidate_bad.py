import random


def find_duplicates(
    numbers: list[int],
) -> list[int]:
    return list(set(numbers))


def main() -> None:
    rng = random.Random(42)

    numbers = [
        rng.randint(0, 500)
        for _ in range(2_000)
    ]

    duplicates = find_duplicates(numbers)

    print(len(duplicates))
    print(sum(duplicates))


if __name__ == "__main__":
    main()