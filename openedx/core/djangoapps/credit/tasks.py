""" This file contains celery tasks for credit course views """

from django.conf import settings

from celery import task
from celery.utils.log import get_task_logger
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

from .api import set_credit_requirements
from openedx.core.djangoapps.credit.exceptions import InvalidCreditRequirements
from openedx.core.djangoapps.credit.models import CreditCourse
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError


LOGGER = get_task_logger(__name__)


# pylint: disable=not-callable
@task(default_retry_delay=settings.CREDIT_TASK_DEFAULT_RETRY_DELAY, max_retries=settings.CREDIT_TASK_MAX_RETRIES)
def update_course_requirements(course_id):
    """ Updates course requirements table for a course.

     Args:
        course_id(str): A string representation of course identifier

    Returns:
        None
    """
    try:
        course_key = CourseKey.from_string(course_id)
        is_credit_course = CreditCourse.is_credit_course(course_key)
        if is_credit_course:
            course = modulestore().get_course(course_key)
            requirements = _get_course_credit_requirements(course)
            set_credit_requirements(course_key, requirements)
    except (InvalidKeyError, ItemNotFoundError, InvalidCreditRequirements) as exc:
        LOGGER.error('Error on adding the requirements for course %s - %s', course_id, unicode(exc))
        raise update_course_requirements.retry(args=[course_id], exc=exc)
    else:
        LOGGER.info('Requirements added for course %s', course_id)


def get_min_grade_for_credit(course):
    """ Returns the min_grade for the credit requirements

     Args:
        course(Course): The course object

    Returns:
        Float value if min_grade of course
    """
    return getattr(course, "min_grade", 0.8)

def _get_course_credit_requirements(course):
    icrv_requirements = _get_credit_course_requirements_xblocks(course)
    min_grade_requirement = _get_min_grade_requirement(course)
    icrv_requirements.extend(min_grade_requirement)
    return icrv_requirements


def _get_min_grade_requirement(course):
    requirement = [
        {
            "namespace": "grade",
            "name": "grade",
            "configuration": {
                "min_grade": get_min_grade_for_credit(course)
            }
        }
    ]
    return requirement


def _get_credit_course_requirements_xblocks(course):
    """ Generates a course structure dictionary for the specified course.

    Args:
        course(Course): The course object

    Returns:
        List of credit requirements xblocks dicts
    """

    blocks_stack = [course]
    requirements_blocks = []
    while blocks_stack:
        curr_block = blocks_stack.pop()
        children = curr_block.get_children() if curr_block.has_children else []
        if _is_credit_requirement(curr_block):
            block = {
                "namespace": curr_block.get_credit_requirement_namespace(),
                "name": curr_block.get_credit_requirement_name(),
                "configuration": ""
            }
            requirements_blocks.append(block)

        # Add this blocks children to the stack so that we can traverse them as well.
        blocks_stack.extend(children)
    return requirements_blocks


def _is_credit_requirement(xblock):
    """ Check if the given xblock is a credit requirement

    Args:
        xblock(XBlock): The given xblock object

    Returns:
        True if xblock is a credit requirement else False
    """
    if callable(getattr(xblock, "is_course_credit_requirement", None)):
        return xblock.is_course_credit_requirement()
    return False
