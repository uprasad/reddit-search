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


def comment_stream(subreddit_list):
    stream_killer = GracefulKiller()
    for comment in reddit.subreddit("+".join(subreddit_list)).stream.comments():
        if stream_killer.kill_now:
            print("Comment stream received SIGTERM")
            return
        # new comment
        comment_details = {
            "body": comment.body,
            "id": comment.id,
            "parent_id": comment.parent_id,
            "subreddit_id": comment.subreddit_id,
            "submission_id": comment.submission.id,
            "submission_title": comment.link_title,
            "gilded": comment.gilded,
            "author": comment.author.name,
            "subreddit": comment.subreddit.display_name.lower(),
            "created_utc": comment.created_utc,
            "permalink": comment.permalink(fast=True)
        }
        pp.pprint(comment_details)
        res = es.index(index="reddit-comments", doc_type=comment_details["subreddit"], body=comment_details, id=comment.id)
        print(res)


def post_stream(subreddit_list):
    print("+".join(subreddit_list))
    stream_killer = GracefulKiller()
    for submission in reddit.subreddit("+".join(subreddit_list)).stream.submissions():
        if stream_killer.kill_now:
            print("Post stream received SIGTERM")
            return
        # new post
        submission_details = {
            "subreddit": submission.subreddit.display_name.lower(),
            "id": submission.id,
            "subreddit_id": submission.subreddit_id,
            "author": submission.author.name,
            "url": submission.url,
            "title": submission.title,
            "created_utc": submission.created_utc
        }
        pp.pprint(submission_details)
        res = es.index(index="reddit-posts", doc_type=submission_details["subreddit"], body=submission_details, id=submission.id)
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
