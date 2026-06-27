from os import environ


LOGLEVEL = environ.get('LOGLEVEL', 'INFO')
SSO_LOGLEVEL = environ.get('SSO_LOGLEVEL', LOGLEVEL)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'netbox_smartlock.sso': {
            'handlers': ['console'],
            'level': SSO_LOGLEVEL,
            'propagate': False,
        },
    },
}
