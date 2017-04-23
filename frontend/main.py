from flask import Flask, render_template, request
import elasticsearch

app = Flask(__name__)
es = elasticsearch.Elasticsearch()


def get_results(query_params):
    """
    Given the search term and filters, get a list of results
    :param query_params: 
    :return: List of search results 
    """



@app.route("/", methods=['GET'])
def main():
    args = request.args.to_dict()
    print(args)
    if args and ("query" in args):
        query = args.get("query")
        query_params = {
            "query": query
        }
        print("Query Params: {}".format(query_params))
        results = get_results(query_params)

    return render_template("index.html", results=results)


if __name__ == "__main__":
    app.run()
