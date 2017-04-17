import pprint
import elasticsearch
import config

reddit = config.init_reddit()

pp = pprint.PrettyPrinter(indent=2)
es = elasticsearch.Elasticsearch()