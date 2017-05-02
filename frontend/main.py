from flask import Flask, render_template, request
import config
import pprint

app = Flask(__name__)
es = config.init_elasticsearch()
pp = pprint.PrettyPrinter()


def get_comment_filter_fields():
    return {"author", "flair", "created_before", "created_after"}


def get_post_filter_fields():
    return {"author", "created_before", "created_after"}


def get_comment_search_body(query):
    # search in comment body
    return {
        "query": {
            "bool": {
                "must": [
                    {"match": {"body": val}} for val in query.split()
                ]
            }
        }
    }


def get_post_search_body(query):
    # search in title or selftext
    return {
        "query": {
            "bool": {
                "should": [
                    {
                        "bool": {
                            "must": [
                                {"match": {"title": val}} for val in query.split()
                            ]
                        }
                    },
                    {
                        "bool": {
                            "must": [
                                {"match": {"selftext": val}} for val in query.split()
                            ]
                        }
                    }
                ]
            }
        }
    }


def get_results(query_params):
    """
    Given the search term and filters, get a list of results
    :param query_params: 
    :return: List of search results 
    """
    query = query_params["query"]
    subreddits = query_params["subreddits"]
    query_type = query_params["type"]
    if not query:
        return None
    if query_type not in ["comments", "posts"]:
        query_type = "comments"
        print("Type of query was not in {}, searching in {}".format(["comments", "posts"], query_type))

    search_body = None
    if query_type == "comments":
        search_body = get_comment_search_body(query)
    elif query_type == "posts":
        search_body = get_post_search_body(query)

    res = es.search(index="reddit-{}".format(query_type), doc_type=subreddits, body=search_body)
    hits = []
    if "hits" in res and "hits" in res["hits"]:
        hits = res["hits"]["hits"]
    print("Num hits: ", len(hits))
    return [hit["_source"] for hit in hits]


@app.route("/", methods=['GET'])
def main():
    args = request.args.to_dict()
    results = None
    query_type = None
    if args:
        query = args.get("query")
        subreddits = "".join(args.get("subreddits").split()).lower()
        query_type = args.get("type")

        query_params = {
            "query": query,
            "subreddits": subreddits,
            "type": query_type
        }
        print("Query Params: {}".format(query_params))
        results = get_results(query_params)

    return render_template("index.html", results=results, query_type=query_type)


if __name__ == "__main__":
    app.run()
