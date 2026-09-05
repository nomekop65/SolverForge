import random


def find_duplicates(
    numbers: list[int],
) -> list[int]:
    seen: set[int] = set()
    duplicates: list[int] = []

    for number in numbers:
        if number in seen:
            if number not in duplicates:
                duplicates.append(number)
        else:
            seen.add(number)

    return duplicates


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