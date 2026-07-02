from tests.mocks.data_generator.documents import DocumentDataGenerator


class DataGenerator:
    """Фасад для генераторов тестовых данных."""

    def __init__(self) -> None:
        self.documents = DocumentDataGenerator()
