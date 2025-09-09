import sys

from src.cli import answer_question


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python app.py \"Your question here\"")
        return 1
    question = " ".join(sys.argv[1:])
    print(answer_question(question))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


