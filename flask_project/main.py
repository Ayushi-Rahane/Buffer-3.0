import pymongo

if __name__ == "__main__":
    # Connect to MongoDB
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["practice_db"]
    collection = db["student"]

    # Insert a document into the collection
    collection.insert_one({"name": "John Doe", "age": 30})
    collection.insert_one({"name": "Jane Smith", "age": 25})
    collection.insert_one({"Full name": "Alice Johnson", "age": 28})
    collection.insert_many([
        {"name": "Bob Brown", "age": 22},
        {"name": "Charlie Black", "age": 35}
    ])

    collection.update_one(
        {"name":"Jane Smith"},
        {"$set": {"age":236}},
        upsert=True
    )
    print("Updation Operation Completed! ")
    print(collection.find_one({"name":"Jane Smith"}))
    # Fetch and print all documents in the collection
    for user in collection.find():
        print(user)