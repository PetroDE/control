"""
While a Controlfile is being read in MetaServices allow for substitutions to be
made. All of the code is here instead of living in controlfile.py so you don't
have to scroll past the Controlfile class
"""

from enum import Enum
import logging

module_logger = logging.getLogger('control.substitution')  # pylint: disable=invalid-name


class Kind(Enum):
    """Enum for things that don't fall into the type system"""
    none = 0
    singular = 1
    list = 2
    dict = 3


DEFAULT_KIND_MAPPING = {
    Kind.singular: str,
    Kind.list: list,
    Kind.dict: dict,
}


def _get_default_of_kind(val):
    return DEFAULT_KIND_MAPPING[_determine_kind(val)]()


def _pick_most_generic(left, right):
    return DEFAULT_KIND_MAPPING[
        sorted([
            _determine_kind(left),
            _determine_kind(right)
        ], key=lambda x: x.value)[-1]
    ]()
    # Make sure to call the constructor so you get a new object of that type
    # instead of something else


def _determine_kind(config_option):
    if isinstance(config_option, dict):
        return Kind.dict
    elif isinstance(config_option, list):
        return Kind.list
    elif config_option is None:
        return Kind.none
    return Kind.singular


def _build_values_for_key(k, op, x, y):  # pylint: disable=invalid-name
    default = _pick_most_generic(x.get(k, None), y.get(k, None))
    return operations[
        (
            _determine_kind(x.get(k, default)),
            _determine_kind(y.get(k, default)),
            op
        )
    ](x.get(k, default), y.get(k, default))


operations = {
    # pylint: disable=unnecessary-lambda
    # aliaeses into the workings of this dict
    'suffix': lambda x, y: operations[(_determine_kind(x), _determine_kind(y), 'suffix')](x, y),
    'prefix': lambda x, y: operations[(_determine_kind(x), _determine_kind(y), 'prefix')](x, y),
    'union': lambda x, y: operations[(_determine_kind(x), _determine_kind(y), 'union')](x, y),
    'replace': lambda x, y: y if y else x,

    # Union ops
    (Kind.singular, Kind.singular, 'union'): lambda x, y: [i for i in [x, y] if i] if x != y else ([x] if x else []),
    (Kind.singular, Kind.list, 'union'): lambda x, yy: [x] + [y for y in yy if y != x],
    (Kind.singular, Kind.dict, 'union'): lambda x, y: {
        k: _build_values_for_key(k, 'union', {'shared': [x]}, y) for k in y.keys() | {'shared'}
    } if x else {k: (v if isinstance(v, list) else [v]) for k, v in y.items()},
    (Kind.list, Kind.singular, 'union'): lambda xx, y: xx + [y] if y not in xx else xx,
    (Kind.list, Kind.list, 'union'): lambda xx, yy: xx + [y for y in yy if y not in xx],
    (Kind.list, Kind.dict, 'union'): lambda xx, y: {
        k: _build_values_for_key(k, 'union', {'shared': xx}, y) for k in y.keys() | {'shared'}
    } if xx else y,
    (Kind.dict, Kind.singular, 'union'): lambda x, y: {
        k: _build_values_for_key(k, 'union', x, {'shared': [y]}) for k in x.keys() | {'shared'}
    },
    (Kind.dict, Kind.list, 'union'): lambda x, yy: {
        k: _build_values_for_key(k, 'union', x, {'shared': yy}) for k in x.keys() | {'shared'}
    } if yy else x,
    (Kind.dict, Kind.dict, 'union'): lambda x, y: {
        k: _build_values_for_key(k, 'union', x, y) for k in x.keys() | y.keys()
    },

    # Suffix Ops
    (Kind.singular, Kind.singular, 'suffix'): '{0}{1}'.format,
    (Kind.singular, Kind.list, 'suffix'): lambda x, y: [x] + y,
    (Kind.list, Kind.singular, 'suffix'): lambda x, y: x + [y],
    (Kind.list, Kind.list, 'suffix'): lambda x, y: x + y,
    (Kind.list, Kind.dict, 'suffix'): lambda x, y: {
        k: _build_values_for_key(k, 'suffix', {'shared': x}, y) for k in y.keys() | {'shared'}
    },
    (Kind.singular, Kind.dict, 'suffix'): lambda x, y: {
        k: _build_values_for_key(k, 'suffix', {'shared': x}, y) for k in y.keys() | {'shared'}
    },
    (Kind.dict, Kind.singular, 'suffix'): lambda x, y: {
        k: _build_values_for_key(k, 'suffix', x, {'shared': y}) for k in x.keys() | {'shared'}
    },
    (Kind.dict, Kind.list, 'suffix'): lambda x, y: {
        k: _build_values_for_key(k, 'suffix', x, {'shared': y}) for k in x.keys() | {'shared'}
    },
    (Kind.dict, Kind.dict, 'suffix'): lambda x, y: {
        k: _build_values_for_key(k, 'suffix', x, y) for k in x.keys() | y.keys()
    },

    # Prefix Ops
    (Kind.singular, Kind.singular, 'prefix'): '{1}{0}'.format,
    (Kind.singular, Kind.list, 'prefix'): lambda x, y: y + [x],
    (Kind.singular, Kind.dict, 'prefix'): lambda x, y: {
        k: _build_values_for_key(k, 'prefix', {'shared': x}, y) for k in y.keys() | {'shared'}
    },
    (Kind.list, Kind.singular, 'prefix'): lambda x, y: [y] + x,
    (Kind.list, Kind.list, 'prefix'): lambda x, y: y + x,
    (Kind.list, Kind.dict, 'prefix'): lambda x, y: {
        k: _build_values_for_key(k, 'prefix', {'shared': x}, y) for k in y.keys() | {'shared'}
    },
    (Kind.dict, Kind.singular, 'prefix'): lambda x, y: {
        k: _build_values_for_key(k, 'prefix', x, {'shared': y}) for k in x.keys() | {'shared'}
    },
    (Kind.dict, Kind.list, 'prefix'): lambda x, y: {
        k: _build_values_for_key(k, 'prefix', x, {'shared': y}) for k in x.keys() | {'shared'}
    },
    (Kind.dict, Kind.dict, 'prefix'): lambda x, y: {
        k: _build_values_for_key(k, 'prefix', x, y) for k in x.keys() | y.keys()
    },
}


def normalize_service(service, opers, variables):
    """
    Takes a service, and options and applies the transforms to the service.

    Allowed args:
    - service: must be service object that was created before hand
    - options: a dict of options that define transforms to a service.
      The format must conform to a Controlfile metaservice options
      definition
    Returns: a service with all the transforms applied and all the variables
             substituted in.
    """
    # We check that the Controlfile only specifies operations we support,
    # that way we aren't trusting a random user to accidentally get a
    # random string eval'd.
    for key, op, val in (
            (key, op, val)
            for key, ops in opers.items()
            for op, val in ops.items() if (op in operations and
                                           key in service.all_options)):
        module_logger.log(11, "service '%s' %sing %s with '%s'.",
                          service.service, op, key, val)
        try:
            replacement = operations[op](service[key], val)
        except KeyError as e:
            module_logger.debug(e)
            module_logger.log(11, "service '%s' missing key '%s'",
                              service.service, key)
            module_logger.log(11, service.__dict__)
            replacement = operations[op](_get_default_of_kind(val), val)
        finally:
            service[key] = replacement
    for key in service.keys():
        try:
            module_logger.debug('now at %s, passing in %i vars', key, len(variables))
            service[key] = _substitute_vars(service[key], variables)
        except KeyError:
            continue
    return service['service'], service


# used exclusively by visit_every_leaf, but defined outside it so it's only compiled once
substitute_vars_decision_dict = {
    # dict, list, str
    (True, False, False): lambda d, vd: {k: _substitute_vars(v, vd) for k, v in d.items()},
    (False, True, False): lambda d, vd: [x.format(**vd) for x in d],
    (False, False, True): lambda d, vd: d.format(**vd),
    (False, False, False): lambda d, vd: d
}


def _substitute_vars(d, var_dict):  # pylint: disable=invalid-name
    """
    Visit every leaf and substitute any variables that are found. This function
    is named poorly, it sounds like it should generically visit every and allow
    a function to be applied to each leaf. It does not. I have no need for that
    right now. If I find a need this will probably be the place that that goes.

    Arguments:
    - d does not necessarily need to be a dict
    - var_dict should be a dictionary of variables that can be kwargs'd into
      format
    """
    # DEBUGGING
    module_logger.debug('now at %s', str(d))
    # DEBUGGING
    return substitute_vars_decision_dict[(
        isinstance(d, dict),
        isinstance(d, list),
        isinstance(d, str)
    )](d, var_dict)


def satisfy_nested_options(outer, inner):
    """
    Merge two Controlfile options segments for nested Controlfiles.

    - Merges appends by having "{{layer_two}}{{layer_one}}"
    - Merges option additions with layer_one.push(layer_two)
    """
    merged = {}
    for key in outer.keys() | inner.keys():
        val = {}
        for op in outer.get(key, {}).keys() | inner.get(key, {}).keys():
            default_value = _pick_most_generic(inner.get(key, {}).get(op, None),
                                               outer.get(key, {}).get(op, None))
            joined = operations[op](inner.get(key, {}).get(op, default_value),
                                    outer.get(key, {}).get(op, default_value))
            if joined:
                val[op] = joined
        merged[key] = val
    return merged
