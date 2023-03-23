import datetime
import logging
import time
import uuid
import os
import sys
import numpy as np
from pymilvus import (
    connections,
    utility,
    FieldSchema, CollectionSchema, DataType,
    Collection, MilvusException,
)

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

dir_ = os.path.dirname
working_dir = dir_(dir_(dir_(os.path.abspath(__file__))))
sys.path.append(working_dir)

from GPT_API import get_gpt3_answer, get_embedding


class VectorDatabase:
    """
    Vector database for the bot. Uses Milvus to store and retrieve vectors.
    """

    def __init__(self, milvus_host='localhost', milvus_port=19530, collection_name=None, index_name=None,
                 milvus_username='', milvus_password='', **kwargs):
        super().__init__(**kwargs)
        # create connection
        connections.connect(host=milvus_host, port=milvus_port, username=milvus_username, password=milvus_password)
        if collection_name is None:
            logger.debug("No collection name provided, using default name: bot_memory")
            collection_name = 'bot_memory'
            # delete collection if it already exists
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)

        if not utility.has_collection(collection_name):
            logger.debug(f"Creating new collection: {collection_name} because it does not exist yet")
            self.milvus = self.create_new_collection(collection_name)

        else:
            logger.debug(f"Collection {collection_name} already exists, loading it")
            self.milvus = Collection(collection_name)
            # self.milvus.load()

        if index_name is None:
            index_name = collection_name + '_index'

        # check if index exists
        if not self.milvus.has_index():
            logger.debug(f"Creating index {index_name} for collection {collection_name}")
            self.create_index()

        self.collection_name = collection_name
        self.milvus.load()
        self.index_name = index_name

    def create_index(self) -> None:
        index = {
            "index_type": "IVF_FLAT",
            "metric_type": "IP",
            "params": {"nlist": 4096},
        }

        self.milvus.create_index("embeddings", index)

    def add_item(self, item: dict) -> str:
        logger.debug(f"Adding item to memory: {item['text']}")
        # item should contain a text, timestamp and author
        # check if fields are present
        if not all([field in item for field in ["text", "timestamp", "author"]]):
            missing_fields = [field for field in ["text", "timestamp", "author"] if field not in item]
            raise ValueError(f"Item is missing the following fields: {missing_fields}")

        # check if item id is present
        if "id" not in item:
            item["id"] = str(uuid.uuid4())

        embedding = self._normalize_vector(get_embedding(item["text"]))
        entities = [
            [item["id"]],
            [item["text"]],
            [item["timestamp"]],
            [item["author"]],
            [embedding]
        ]
        self.milvus.insert(entities)
        logger.info(f"Added item to memory: {item['text']}")
        return item["id"]

    def add_information(self, text: str, author="unknown") -> str:
        timestamp = datetime.datetime.now().timestamp()
        item = {
            "id": str(uuid.uuid4()),
            "text": text,
            "timestamp": timestamp,
            "author": author
        }
        self.add_item(item)
        return item["id"]

    def get_by_id(self, item_id: str) -> dict:
        res = self.milvus.query(
            expr="""id like "{}" """.format(item_id),
            offset=0,
            limit=1,
            output_fields=["id", "text", "timestamp", "author"],
            consistency_level="Strong"
        )
        print(res)
        return {"id": res[0].get("id"), "text": res[0].get("text"), "timestamp": res[0].get("timestamp"),
                "author": res[0].get("author")}

    def get_similar_by_vector(self, vector: np.ndarray | list, top_k=10, filter=None, threshold=0.7) -> list:
        # logger.debug(f"Searching for similar memories to {vector}")
        for i in range(2):
            try:

                search_params = {
                    "metric_type": "IP",
                    "params": {"nprobe": 128},
                }

                result = self.milvus.search([vector], "embeddings", search_params, limit=top_k,
                                            output_fields=["id", "text", "timestamp", "author"], expr=filter)

                # filter by threshold
                result = [res for res in result[0] if res.distance > threshold]

                if len(result) > 0:
                    result = [
                        {"id": res.entity.get("id"), "text": res.entity.get("text"),
                         "timestamp": res.entity.get("timestamp"),
                         "author": res.entity.get("author"),
                         "distance": res.distance} for res in result]

                return result
            except MilvusException as e:
                if e.code == 1:
                    self.create_index()

    def get_similar_by_text(self, text: str, top_k=10, filter=None, threshold=0.7) -> list:
        logger.debug(f"Searching for similar entries to {text}")
        vector = self._normalize_vector(get_embedding(text))
        return self.get_similar_by_vector(vector, top_k, filter, threshold)

    @staticmethod
    def _normalize_vector(vector: np.ndarray) -> np.ndarray:
        """Normalizes a vector to unit length.
        -> This is needed to implement cosine similarity on Milvus."""
        return vector / np.linalg.norm(vector)  #

    def update_item(self, item_id: str, new_item: dict) -> None:
        logger.debug(f"Updating item in memory: {item_id}")

        # fetch old item
        old_item = self.get_by_id(item_id)
        # update old item with new item
        old_item.update(new_item)
        # delete old item
        self.delete_item(item_id)
        # add new item
        self.add_item(old_item)

    def create_new_collection(self, collection_name: str) -> Collection:
        # self.milvus.release()
        logger.debug("Creating new collection")
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=37),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2000),
            FieldSchema(name="timestamp", dtype=DataType.DOUBLE),
            FieldSchema(name="author", dtype=DataType.VARCHAR, max_length=200),
            FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=1536)
        ]
        schema = CollectionSchema(fields, collection_name + "Description")
        collection = Collection(collection_name, schema)

        return collection

    def delete_item(self, item_id: str) -> None:
        logger.debug(f"Deleting item from memory: {item_id}")
        self.milvus.delete(expr="id in ['{}']".format(item_id))
        logger.info(f"Deleted item from memory: {item_id}")

    def clear(self) -> None:
        logger.debug(f"Clearing {self.collection_name} collection")
        self.milvus.drop()
        self.milvus = self.create_new_collection(self.collection_name)
        self.create_index()
        self.milvus.flush()
        self.milvus.load()


if __name__ == "__main__":
    # create a new memory
    db = VectorDatabase(collection_name="test")
    db.clear()
    # add some information
    id_1 = db.add_information("I am happy")
    db.add_information("I am sad")
    db.add_information("I am angry")

    # get similar entries
    print(db.get_similar_by_text("I am happy"))
    print(db.get_similar_by_text("I am sad"))
    print(db.get_similar_by_text("I am angry"))

    # update an entry
    db.update_item(id_1, {"text": "I am happy and sad"})

    # wait 5s
    time.sleep(5)

    # get similar entries
    print(db.get_similar_by_text("I am happy and sad"))
