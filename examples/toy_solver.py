def find_duplicates(numbers: list[int]) -> list[int]:
    duplicates = []

    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):
            if numbers[i] == numbers[j]:
                if numbers[i] not in duplicates:
                    duplicates.append(numbers[i])

    return duplicates


def main() -> None:
    numbers = [
        5,
        3,
        8,
        5,
        2,
        3,
        9,
        1,
        8,
        7,
    ]

    print(find_duplicates(numbers))


if __name__ == "__main__":
    main()