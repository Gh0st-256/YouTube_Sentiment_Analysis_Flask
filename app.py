from flask import Flask, render_template, request
from src import youtube_data_module as ydt
from src import viz
import pandas as pd
import os
import logging
import sys

logger = logging.getLogger('app_logger')
handler = logging.StreamHandler(sys.stderr)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

API_KEY = os.getenv('YOUTUBE_API_KEY')

app = Flask(__name__)


@app.route('/')
def home():  # put application's code here
    return render_template('layout.html')


@app.route('/select_vid')
def select_vid():
    """This page returns search results when the user clicks on the 'search video' button"""
    result_dictionary = request.args
    query = result_dictionary['query']
    youtube = ydt.youtubeAPIkey(API_KEY)
    query_result = ydt.youtubeSearchListStatistics(youtube, q=query)

    return render_template(
        'select_video.html',
        query_result=query_result,
        query=query
    )


@app.route('/vid_comments')
def vid_comments():
    """This page basically returns a video comments analysis as soon as the user hits 'see video comment analysis'
    button """
    video_id = request.args.get('video_id')
    youtube = ydt.youtubeAPIkey(API_KEY)

    logger.info('getting all the comments')
    all_snippets = ydt.get_all_comments(youtube, video_id)
    logger.info('Writing Comments to dictionary')
    comment_dict = ydt.extract_comments(all_snippets)

    image_names = []
    logger.info('Generating wordcloud')
    comment_string = ydt.concat_comments(comment_dict)
    video_title = video_id
    image_names.append(
        viz.create_wordcloud(comment_string, stopwords=None, video_id=video_id, channel_title=video_title))
    comment_df = ydt.comments_to_df(all_snippets)
    comment_sentiment = ydt.analyze_comment_sentiments(comment_df)
    comment_sentiment2, pos_sent, neg_sent = viz.split_sentiment_pos_neg(comment_sentiment)
    image_names.append(viz.lineplot_cumsum_video_comments(comment_sentiment2, video_id))
    image_names.append(viz.lineplot_cumsum_video_comments_pos_neg(comment_sentiment2, pos_sent, neg_sent, video_id))
    image_names.append(viz.scatterplot_sentiment_likecount(comment_sentiment2, pos_sent, neg_sent, video_id))

    # this is for Correlation Calculation
    like_count_sentiment_corr = round(comment_sentiment2.corr().loc['like_count'][5], 2)

    return render_template(
        'video_comments.html',
        image_names=image_names,
        like_count_sentiment_corr=like_count_sentiment_corr

    )


@app.route('/select_channels', methods=['GET', 'POST'])
def select_channels():
    """This page in particular is supposed to return search results for the channel querries
    a user inputs and hits the 'search channels' button"""

    result_dictionary = request.args
    channel_names = []

    for channel_name in result_dictionary:
        if len(result_dictionary.get(channel_name)) > 0:
            channel_names.append(result_dictionary[channel_name])

    youtube = ydt.youtubeAPIkey(API_KEY)
    query_results = {}

    for cn in channel_names:
        result = ydt.youtubeSearchList(youtube, channel_id=None, q=cn, maxResults=100, type='channel')
        query_results[cn] = result

    return render_template(
        'select_channels.html',
        query_results=query_results
    )


@app.route('/channels', methods=['GET', 'POST'])
def channels():
    """Majorly this page all its supposed to do is to return the channel
    comparison analysis when a user selects at least one channel with a radio button
    then hits 'Compare channels now' button"""
    result_dictionary = request.args

    channel_ids = []
    for c_id in result_dictionary:
        if len(result_dictionary[c_id]) == 24:
            channel_ids.append(result_dictionary[c_id])

    youtube = ydt.youtubeAPIkey(API_KEY)
    video_df = ydt.get_channel_video_df(youtube, channel_ids)

    image_names = []
    image_names.append(viz.barplot_channel_video_count(video_df, channel_ids))
    image_names.append(viz.barplot_links(video_df, channel_ids))

    channel_titles = []
    for channel_id in channel_ids:
        channel_video_df = video_df[video_df['channel_id'] == channel_id]
        channel_title = channel_video_df['channel_title'].unique()[0]
        channel_titles.append(channel_title)
        image_names.append(
            viz.histogram_video_duration_count_single(channel_video_df, channel_id, channel_title=channel_title))
        channel_video_series = channel_video_df['tags']
        wordcloud_string = ydt.concat_listelements(channel_video_series)
        image_names.append(
            viz.create_wordcloud(wordcloud_string, stopwords=None, video_id=channel_id, channel_title=channel_title))

    df_table = viz.top_videos(video_df, metric='view', n=5)

    return render_template(
        'channels.html',
        result_dictionary=result_dictionary,
        video_df=video_df,
        image_names=image_names,
        channel_ids=channel_ids,
        channel_titles=channel_titles,
        tables=[df_table.to_html(index=False, classes='table-stripped')],
    )


if __name__ == '__main__':
    app.run()
