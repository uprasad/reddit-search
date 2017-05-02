import argparse
import multiprocessing
import time
import sys
import signal
import config
import pprint


reddit = config.init_reddit()
es = config.init_elasticsearch()
pp = pprint.PrettyPrinter()


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGTERM, self.sigterm_handler)
        signal.signal(signal.SIGINT, self.sigterm_handler)

    def sigterm_handler(self, signum, frame):
        self.kill_now = True


def get_comment_details(comment):
    return {
        "body": comment.body,
        "id": comment.id,
        "parent_id": comment.parent_id,
        "subreddit_id": comment.subreddit_id,
        "post_id": comment.submission.id,
        "title": comment.link_title,
        "author": comment.author.name,
        "subreddit": comment.subreddit.display_name,
        "created_utc": comment.created_utc,
        "permalink": comment.permalink(fast=True),
        "flair": comment.author_flair_text
    }


def comment_stream(subreddits):
    stream_killer = GracefulKiller()
    for comment in reddit.subreddit("+".join(subreddits)).stream.comments():
        if stream_killer.kill_now:
            print("Comment stream received SIGTERM")
            return
        # new comment
        comment_details = get_comment_details(comment)
        pp.pprint(comment_details)
        res = es.index(index="reddit-comments", doc_type=comment_details["subreddit"].lower(),
                       body=comment_details, id=comment.id)
        print(res)


def get_post_details(post):
    return {
        "subreddit": post.subreddit.display_name,
        "id": post.id,
        "subreddit_id": post.subreddit_id,
        "author": post.author.name,
        "url": post.url,
        "title": post.title,
        "selftext": post.selftext,
        "created_utc": post.created_utc,
        "flair": post.link_flair_text
    }


def post_stream(subreddits):
    print("+".join(subreddits))
    stream_killer = GracefulKiller()
    for post in reddit.subreddit("+".join(subreddits)).stream.submissions():
        if stream_killer.kill_now:
            print("Post stream received SIGTERM")
            return
        # new post
        post_details = get_post_details(post)
        pp.pprint(post_details)
        res = es.index(index="reddit-posts", doc_type=post_details["subreddit"].lower(), body=post_details, id=post.id)
        print(res)


if __name__ == "__main__":
    if not es.ping():
        print("Elasticsearch cluster is not up, exiting")
        sys.exit()

    parser = argparse.ArgumentParser(description="Stream and index comments and post from subreddits")
    parser.add_argument("-s", "--subreddits", nargs="+", help="<Required> list of subreddits", required=True, type=str)
    args = parser.parse_args()
    subreddit_list = args.subreddits

    # start comment stream
    comment_stream_process = multiprocessing.Process(target=comment_stream, args=(subreddit_list,),
                                                     name="comment-stream")
    comment_stream_process.daemon = True
    comment_stream_process.start()

    # start post stream
    post_stream_process = multiprocessing.Process(target=post_stream, args=(subreddit_list,), name="post-stream")
    post_stream_process.daemon = False
    post_stream_process.start()

    killer = GracefulKiller()
    while comment_stream_process.is_alive() and post_stream_process.is_alive():
        time.sleep(1)
        if killer.kill_now:
            print("Main received SIGTERM")
            comment_stream_process.terminate()
            post_stream_process.terminate()
            sys.exit()
