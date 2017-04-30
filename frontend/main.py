from flask import Flask, render_template, request
import config
import pprint

app = Flask(__name__)
es = config.init_elasticsearch()
pp = pprint.PrettyPrinter()


def get_results(query_params):
    """
    Given the search term and filters, get a list of results
    :param query_params: 
    :return: List of search results 
    """
    query = query_params["query"]
    subreddits = query_params["subreddits"]
    if not query:
        return None

    haves = [{"match": {"body": val}} for val in query.split()]
    should_match = {
        "query": {
            "bool": {
                "should": haves
            }
        }
    }
    must_match = {
        "query": {
            "bool": {
                "must": haves
            }
        }
    }
    phrase_match = {
        "query": {
            "match_phrase": {"body": query}
        }
    }
    res = es.search(index="reddit-comments", doc_type=subreddits, body=must_match)
    hits = []
    if "hits" in res and "hits" in res["hits"]:
        hits = res["hits"]["hits"]
    return [hit["_source"] for hit in hits]


@app.route("/", methods=['GET'])
def main():
    args = request.args.to_dict()
    results = None
    if args:
        query = args.get("query")
        subreddits = "".join(args.get("subreddits").split())

        query_params = {
            "query": query,
            "subreddits": subreddits
        }
        print("Query Params: {}".format(query_params))
        results = get_results(query_params)

    return render_template("index.html", results=results)


if __name__ == "__main__":
    app.run()
