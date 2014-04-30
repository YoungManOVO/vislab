import flask
import vislab.collection
import vislab.datasets
import vislab.utils.redis_q
import util

app = flask.Flask(__name__)
collection = vislab.collection.Collection()
collection_name = 'flickr'


@app.route('/')
def index():
    return flask.redirect(flask.url_for('similar_to_random'))


@app.route('/similar_to_random')
def similar_to_random():
    # TODO: figure this out
    image_id = collection.get_random_id(collection_name)
    return flask.redirect(flask.url_for(
        'similar_to_id', image_id=image_id))


@app.route('/similar_to/<image_id>')
def similar_to_id(image_id):
    """
    This function does double duty: it returns both the rendered HTML
    and the JSON results, depending on whether the json arg is set.
    This keeps the parameter-parsing logic in one place.
    """
    select_options = {
        'feature': {
            'name': 'feature',
            'options': ['deep fc6', 'style scores']
        },
        'distance': {
            'name': 'distance_metric',
            'options': ['euclidean', 'manhattan']
        }
    }

    args = util.get_query_args(
        defaults={
            'feature': 'deep fc6',
            'distance': 'euclidean',
            'page': 1,
        },
        types={
            'page': int
        }
    )

    prediction_options = ['all'] + [
        'pred_{}'.format(x)
        for x in vislab.datasets.flickr.underscored_style_names
    ]

    filter_conditions_list = []
    for prediction in prediction_options:
        filter_conditions = {}
        if prediction != 'all':
            filter_conditions.update({prediction: '> 0'})
        filter_conditions_list.append(filter_conditions)

    kwargs = {
        'image_id': image_id,
        'feature': args['feature'],
        'distance': args['distance'],
        'page': args['page'],
        'filter_conditions_list': filter_conditions_list,
        'results_per_page': 8
    }
    method_name = 'nn_by_id_many_filters'
    job = vislab.utils.redis_q.submit_job(
        method_name, kwargs, 'similarity_server')
    results_sets = vislab.utils.redis_q.get_return_value(job)

    for results_data, prediction in zip(results_sets, prediction_options):
        results_data['title'] = prediction

    image_info = collection.find_by_id(image_id, collection_name)

    return flask.render_template(
        'similarity.html', args=args,
        select_options=select_options,
        image_info=image_info,
        results_sets=results_sets
    )


if __name__ == '__main__':
    util.start_from_terminal(app)
