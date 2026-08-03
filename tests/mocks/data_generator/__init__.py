from tests.mocks.data_generator.blogposts import BlogpostDataGenerator
from tests.mocks.data_generator.documents import DocumentDataGenerator
from tests.mocks.data_generator.sales import SalesDataGenerator


class DataGenerator:
    """Фасад для генераторов тестовых данных."""

    def __init__(self) -> None:
        self.documents = DocumentDataGenerator()
        self.blogposts = BlogpostDataGenerator()
        self.sales = SalesDataGenerator()
