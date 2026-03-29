import fire

class DcmFrameworkRunner:
    def __init__(self):
        pass

    class util:
        @staticmethod
        def hello():
            print("hello.")


def main():
    fire.Fire(DcmFrameworkRunner)

if __name__ == "__main__":
    main()