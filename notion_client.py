"""
    ./notion_client.py

    A simple Notion API Client that I coded for fun.
"""
import requests
import json


class GetDatabaseException(Exception):
    pass


class QueryDatabaseException(Exception):
    pass


class GetPageException(Exception):
    pass


class CreatePageException(Exception):
    pass


class NotionAPIClient:
    """
    A simple Notion API Client, fetching things (not all endpoints are implemented).
    """

    def __init__(self, token):
        self.__token = token
        self.__headers = {
            "Authorization": f"Bearer {self.__token}",
            "Notion-Version": "2021-08-16",
            "Content-Type": "application/json",
        }

    @classmethod
    def str_to_page_id(self, string: str) -> str:

        # Building a page id as 8-4-4-12 from string
        page_id = string[:8] + "-" + string[8:12] + "-" + string[12:16] + "-" + string[16:20] + "-" + string[20:]

        return page_id

    def get_database(self, database_id) -> dict:
        """Gets basic information about a database from its ID.

        Args:
            database_id (str): The ID of the database to get.

        Returns:
            dict: A dictionary containing the database's information.
        """
        # Database URL
        url = f"https://api.notion.com/v1/databases/{database_id}"

        response = requests.get(url, headers=self.__headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise GetDatabaseException(f"Error while getting database: {response.status_code}")

    def query_database(self, query: dict, database_id: str) -> dict:
        """Queries in a given database.

        Args:
            query (dict): The query to execute.
            database_id (str): The ID of the database to query.

        Returns:
            dict: A dictionary containing the query's results.
        """

        url = f"https://api.notion.com/v1/databases/{database_id}/query"

        response = requests.request("POST", url=url, data=json.dumps(query), headers=self.__headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise QueryDatabaseException(f"Error while querying database: {response.status_code}")

    def get_page(self, page_id: str) -> dict:
        """Gets a page from its ID.

        Args:
            page_id (str): the page ID

        Returns:
            dict: the page's data
        """

        url = f"https://api.notion.com/v1/pages/{page_id}"

        response = requests.get(url, headers=self.__headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise GetPageException(f"Error while retrieving the page: {response.status_code}")

    def create_page(self, page_data: str) -> None:
        """Creates a new page

        Args:
            page_data (str): the page data dict
        """

        url = f"https://api.notion.com/v1/pages"

        response = requests.post(url, data=json.dumps(page_data), headers=self.__headers)

        if response.status_code != 200:
            raise CreatePageException(f"Error while creating the page: {response.status_code}")
