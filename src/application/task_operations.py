import logging
from application.models.application import ProductOffering

from application.models.application import Application, ApplicationStage
from application.models.blend_status import BlendStatus
from application.models.task_category import TaskCategory
from application.models.task_name import TaskName
from application.models.task_status import TaskStatus
from application.models.task_progress import TaskProgress
from application.models.task import Task
from application.models.current_home import COMPLETED_LISTING_STATUSES

logger = logging.getLogger(__name__)


def add_task_if_active(application, name):
    task = Task.objects.get(name=name)

    if task.is_active():
        defaults = {'status': TaskProgress.NOT_STARTED}

        TaskStatus.objects.get_or_create(application=application, task_obj=Task.objects.get(name=name),
                                         defaults=defaults)
    else:
        logger.error("Unable to add task to inactive application", extra=dict(
            type="cant_add_task_to_inactive_application",
            task_name=name,
            application_id=application.id,
            task_id=task.id
        ))

def delete_task_if_exists(application, name):
    application.task_statuses.filter(task_obj__name=name).delete()

def real_estate_agent_status(application):
    status = TaskProgress.NOT_STARTED

    if application.listing_agent is not None and application.buying_agent is not None:
        if application.listing_agent.has_name_and_email() and application.buying_agent.has_name_and_email():
            return TaskProgress.COMPLETED

    if application.buying_agent is not None and application.needs_listing_agent:
        if application.buying_agent.has_name_and_email():
            return TaskProgress.COMPLETED

    if application.listing_agent is not None and application.needs_buying_agent:
        if application.listing_agent.has_name_and_email():
            return TaskProgress.COMPLETED

    if application.needs_listing_agent and application.needs_buying_agent:
        return TaskProgress.COMPLETED

    return status


def lender_status(application: Application):
    if application.needs_lender:
        return TaskProgress.COMPLETED
    elif application.mortgage_lender is not None:
        if application.mortgage_lender.is_complete():
            return TaskProgress.COMPLETED
    return TaskProgress.NOT_STARTED


def buying_situation_status(application):
    return TaskProgress.COMPLETED


def disclosures_status(application):
    status_array = [acknowledgement.is_acknowledged is True for acknowledgement in application.acknowledgements.filter(disclosure__active=True)]

    if len(status_array) == 0:
        return TaskProgress.COMPLETED
    elif all(status_array):
        return TaskProgress.COMPLETED
    elif any(status_array):
        return TaskProgress.IN_PROGRESS
    else:
        return TaskProgress.NOT_STARTED


def existing_property_status(application):
    if application.current_home:
        if application.current_home.listing_status in COMPLETED_LISTING_STATUSES or \
                application.current_home.customer_value_opinion:
            return TaskProgress.COMPLETED
        else:
            return TaskProgress.NOT_STARTED
    else:
        # this represents the scenario where they somehow got this task but dont actually have an existing property
        return TaskProgress.COMPLETED


def photo_upload_status(application):
    if application.current_home is not None:
        current_home = application.current_home
        if application.current_home.listing_status in COMPLETED_LISTING_STATUSES or current_home.images.count() > 4:
            return TaskProgress.COMPLETED
        elif current_home.images.count() > 0:
            return TaskProgress.IN_PROGRESS
        else:
            return TaskProgress.NOT_STARTED
    else:
        return TaskProgress.COMPLETED


def homeward_mortgage_status(application):
    if application.blend_status is None or application.blend_status == '':
        return TaskProgress.NOT_STARTED
    elif application.blend_status.lower() == BlendStatus.APPLICATION_CREATED.lower() or \
            BlendStatus.APPLICATION_IN_PROGRESS_PATTERN.match(application.blend_status):
        return TaskProgress.IN_PROGRESS
    elif application.blend_status.lower() == BlendStatus.APPLICATION_ARCHIVED.lower():
        return TaskProgress.IN_PROGRESS
    elif BlendStatus.APPLICATION_COMPLETED_PATTERN.match(application.blend_status):
        if application.stage in ApplicationStage.POST_APPROVED_STAGES:
            return TaskProgress.COMPLETED
        else:
            return TaskProgress.UNDER_REVIEW
    else:
        logger.error(f"Encountered unexpected blend_status for application {application.id}", extra=dict(
            type="unexpected_blend_status_for_application",
            application_id=application.id,
            application_blend_status=application.blend_status
        ))
        return TaskProgress.UNDER_REVIEW


def run_task_operations(application):
    handle_application_tasks_assignment(application)
    update_application_tasks(application)


def handle_application_tasks_assignment(application: Application):
    handle_default_tasks_assignment(application)
    handle_current_home_tasks_assignment(application)
    handle_homeward_mortgage_task_assignment(application)


def handle_homeward_mortgage_task_assignment(application):
    state = application.get_purchasing_state()

    if state:
        mortgage_task = Task.objects.filter(state=state.lower(),
                                            category=TaskCategory.HOMEWARD_MORTGAGE)
        if mortgage_task.count() > 1:
            logger.error(f"Found multiple mortgage tasks for state {state.lower()}", extra=dict(
                type="multiple_mortgage_tasks_for_state",
                category=TaskCategory.HOMEWARD_MORTGAGE,
                state=state.lower(),
                application_id=application.id
            ))
            raise Exception("looking for one mortgage task for {}, found {}!"
                            .format(application.get_current_home_state(), mortgage_task.count()))
        elif mortgage_task.count() == 1 and mortgage_task.first().is_active():
            add_task_if_active(application=application, name=mortgage_task.first().name)


def handle_current_home_tasks_assignment(application):
    if application.current_home and application.product_offering == ProductOffering.BUY_SELL:
        add_task_if_active(application=application, name=TaskName.PHOTO_UPLOAD)
        add_task_if_active(application=application, name=TaskName.EXISTING_PROPERTY)
    elif application.product_offering == ProductOffering.BUY_ONLY:
        delete_task_if_exists(application=application, name=TaskName.PHOTO_UPLOAD)
        delete_task_if_exists(application=application, name=TaskName.EXISTING_PROPERTY)


def handle_default_tasks_assignment(application):
    add_task_if_active(application=application, name=TaskName.REAL_ESTATE_AGENT)
    add_task_if_active(application=application, name=TaskName.BUYING_SITUATION)

    if application.has_disclosures():
        add_task_if_active(application=application, name=TaskName.DISCLOSURES)



def update_application_tasks(application):
    status_checks = {
        TaskCategory.REAL_ESTATE_AGENT: real_estate_agent_status,
        TaskCategory.LENDER: lender_status,
        TaskCategory.BUYING_SITUATION: buying_situation_status,
        TaskCategory.DISCLOSURES: disclosures_status,
        TaskCategory.EXISTING_PROPERTY: existing_property_status,
        TaskCategory.PHOTO_UPLOAD: photo_upload_status,
        TaskCategory.HOMEWARD_MORTGAGE: homeward_mortgage_status
    }
    for task_status in application.task_statuses.all():
        updated_status = status_checks[task_status.task_obj.category](application)
        task_status.status = updated_status
        task_status.save()


def update_photo_task(application):
    if application.current_home:
        add_task_if_active(application, TaskName.PHOTO_UPLOAD)
        task_status = application.task_statuses.get(task_obj__name=TaskName.PHOTO_UPLOAD)
        task_status.status = photo_upload_status(application)
        task_status.save()


def update_current_home_task(application):
    if application.current_home:
        add_task_if_active(application, TaskName.EXISTING_PROPERTY)
        task_status = application.task_statuses.get(task_obj__name=TaskName.EXISTING_PROPERTY)
        task_status.status = existing_property_status(application)
        task_status.save()
