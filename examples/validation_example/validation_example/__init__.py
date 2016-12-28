import schema


def hello():
    """usage: say hello"""
    print('Hello!')


def hiya(name):
    """usage: say hiya <name>"""
    print('Hiya, {name}!'.format(name=name))


def validate_name(**cli_args):
    assert '--name' in cli_args
    assert str(cli_args['--name'])
    assert len(cli_args['--name'])
    cli_args['name'] = cli_args.pop('--name')
    return cli_args

hiya.validate = validate_name
