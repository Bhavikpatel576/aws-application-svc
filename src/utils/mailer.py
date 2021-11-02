from typing import List

from application.models.application import ProductOffering
from application.models.customer import Customer
from application.models.internal_support_user import InternalSupportUser
from application.models.new_home_purchase import NewHomePurchase
from application.models.offer import Offer
from application.models.real_estate_agent import RealEstateAgent
from utils import hubspot

UNDER_REVIEW = "Under Review"
DEFAULT_AGENT_NAME = "your agent"


def get_address_if_applicable(application):
    if application.product_offering == ProductOffering.BUY_ONLY:
        return "Not Applicable"
    if application.current_home:
        if application.product_offering == ProductOffering.BUY_SELL and application.current_home.address:
            return application.current_home.address.street
    else:
        return None


def format_currency_for_email(currency_value):
    if currency_value:
        return f"${round(currency_value):,}"
    else:
        return UNDER_REVIEW


def send_photo_task_complete_notification(first_name, last_name, link):
    return hubspot.send_photo_task_complete_notification(first_name, last_name, link)


def send_hca_referral_sign_up_notification(agent, customer_name, customer_first_name):
    return hubspot.send_hca_referral_sign_up_notification(agent, customer_name, customer_first_name)


def send_agent_registration_notification(agent_email: str, agent_first_name: str, customer_first_name: str):
    return hubspot.send_agent_registration_notification(agent_email, agent_first_name, customer_first_name)


def send_application_under_review(customer_name: str, customer_email: str, application_id: str,
                                  cc_email_list: List[str], loan_advisor_first_name: str = None,
                                  loan_advisor_last_name: str = None, loan_advisor_call_link: str = None,
                                  loan_advisor_phone: str = None):
    return hubspot.send_application_under_review(customer_name, customer_email, application_id,
                                                 cc_email_list, loan_advisor_first_name, loan_advisor_last_name,
                                                 loan_advisor_call_link, loan_advisor_phone)


def send_non_hw_mortgage_candidate_approval(customer_email: str, customer_name: str, preapproval_amount,
                                            estimated_down_payment, current_home_address: str, cc_email_list: List[str],
                                            from_email: str, cx_first_name: str = None, cx_last_name: str = None,
                                            cx_call_link: str = None, cx_email: str = None, cx_phone: str = None):
    formatted_amount = format_currency_for_email(preapproval_amount)
    formatted_estimated_down_payment = format_currency_for_email(estimated_down_payment)
    return hubspot.send_non_hw_mortgage_candidate_approval(customer_email, customer_name, formatted_amount,
                                                           formatted_estimated_down_payment, current_home_address,
                                                           cc_email_list, from_email, cx_first_name, cx_last_name,
                                                           cx_call_link, cx_email, cx_phone)

def send_hw_mortgage_candidate_approval(customer_email: str, 
                                        homeward_owner_email: str,
                                        customer_name: str, 
                                        preapproval_amount,
                                        estimated_down_payment,
                                        current_home_address: str,
                                        cc_email_list: List[str],
                                        loan_advisor_first_name: str = None,
                                        loan_advisor_last_name: str = None, 
                                        loan_advisor_phone: str = None,
                                        loan_advisor_email: str = None, 
                                        loan_advisor_call_link: str= None):
    formatted_amount = format_currency_for_email(preapproval_amount)
    formatted_estimated_down_payment = format_currency_for_email(estimated_down_payment)
    return hubspot.send_hw_mortgage_candidate_approval(customer_email, homeward_owner_email, customer_name, formatted_amount, formatted_estimated_down_payment, current_home_address, cc_email_list, loan_advisor_first_name, loan_advisor_last_name, loan_advisor_phone, loan_advisor_email, loan_advisor_call_link)


def send_agent_instructions(agent_name, agent_email: str, customer_name: str, application_id: str,
                            cc_email_list: List[str], from_email: str, cx_first_name: str = None,
                            cx_last_name: str = None, cx_call_link: str = None):
    return hubspot.send_agent_instructions(agent_name, agent_email, customer_name, application_id, cc_email_list,
                                           from_email, cx_first_name, cx_last_name, cx_call_link)


def send_unacknowledged_service_agreement_email(customer: Customer):
    return hubspot.send_unacknowledged_service_agreement_email(customer)


def send_offer_submitted(customer: Customer, offer: Offer, offer_price: int, cc_email_list: List[str], from_email: str):
    return hubspot.send_offer_submitted(customer, offer, offer_price, cc_email_list, from_email)


def send_offer_submitted_agent(agent_email: str, agent_name: str, new_home_street: str, cx_first_name: str,
                               cx_last_name: str, homeward_owner_email: str, cc_email_list: List[str]):
    return hubspot.send_offer_submitted_agent(agent_email, agent_name, new_home_street, cx_first_name, cx_last_name,
                                              homeward_owner_email, cc_email_list)


def send_offer_accepted(customer_email: str, customer_name: str, new_home_purchase: NewHomePurchase,
                        floor_price: str, cc_email_list: List[str], from_email: str):
    return hubspot.send_offer_accepted(customer_email, customer_name, new_home_purchase, floor_price, cc_email_list,
                                       from_email)


def send_purchase_price_updated(customer: Customer, preapproval_amount: int, cc_email_list: List[str],
                                contact_first_name: str, contact_last_name: str, contact_email: str,
                                contact_schedule_a_call_url: str):
    return hubspot.send_purchase_price_updated(customer, preapproval_amount, cc_email_list, contact_first_name,
                                               contact_last_name, contact_email,contact_schedule_a_call_url)


def send_expiring_approval_email(customer_email: str, customer_name: str, agent_email: str, homeward_owner_email: str):
    return hubspot.send_expiring_approval_email(customer_email, customer_name, agent_email, homeward_owner_email)


def send_pre_homeward_close(customer: Customer, new_home_purchase: NewHomePurchase, cc_email_list: List[str],
                            from_email: str):
    return hubspot.send_pre_homeward_close(customer, new_home_purchase, cc_email_list, from_email)


def send_pre_customer_close(customer: Customer, new_home_purchase: NewHomePurchase, cc_email_list: List[str],
                            cx_manager: InternalSupportUser, from_email: str):
    return hubspot.send_pre_customer_close(customer, new_home_purchase, cc_email_list, cx_manager, from_email)


def send_agent_pre_customer_close(customer_name: str, agent_name: str, agent_email: str,
                                  address_street: str, close_date: str, homeward_owner_email: str,
                                  transaction_coordinator_email=None):
    return hubspot.send_agent_pre_customer_close(customer_name, agent_name, agent_email, address_street, close_date,
                                                 homeward_owner_email, transaction_coordinator_email)


def send_agent_customer_close(agent_name: str, agent_email: str, customer_name: str, new_home_street: str,
                              homeward_owner_email: str, transaction_coordinator_email=None):
    return hubspot.send_agent_customer_close(agent_name, agent_email, customer_name, new_home_street,
                                             homeward_owner_email, transaction_coordinator_email)


def send_homeward_close(customer: Customer, cc_email_list: List[str], from_email: str):
    return hubspot.send_homeward_close(customer, cc_email_list, from_email)


def send_customer_close(name: str, email: str, street: str, cc_email_list: List[str], from_email: str):
    return hubspot.send_customer_close(name, email, street, cc_email_list, from_email)


def send_incomplete_account_notification(customer: Customer, buying_agent: RealEstateAgent, resume_link: str,
                                         notification_name: str):
    return hubspot.send_incomplete_account_notification(customer, buying_agent, resume_link, notification_name)


def send_agent_referral_welcome_email(customer: Customer, buying_agent: RealEstateAgent,
                                      pricing_link: str):
    return hubspot.send_agent_referral_welcome_email(customer, buying_agent, pricing_link)


def send_cma_request(agent_email: str, agent_name: str, customer_name: str, current_home_street: str):
    return hubspot.send_cma_request(agent_email, agent_name, customer_name, current_home_street)


def send_cx_manager_message(cx_manager_email: str, message: str, customer_name: str, customer_email: str, customer_sf_url: str):
    return hubspot.send_cx_manager_message(cx_manager_email, message, customer_name, customer_email, customer_sf_url)


def send_incomplete_agent_referral_reminder(agent_email: str, agent_first_name: str, resume_link: str):
    return hubspot.send_incomplete_agent_referral_reminder(agent_email, agent_first_name, resume_link)


def send_saved_quote_cta(agent_first_name: str, agent_email: str, resume_link: str):
    return hubspot.send_saved_quote_cta(agent_first_name, agent_email, resume_link)


def send_fast_track_resume_email(buy_agent_email: str, buy_agent_name: str, customer_name: str, customer_first_name: str,
                                 customer_email: str, resume_link: str):
    return hubspot.send_fast_track_resume_email(buy_agent_email, buy_agent_name, customer_name, customer_first_name,
                                                customer_email, resume_link)


def send_vpal_incomplete_email(buying_agent_email, customer_first_name, customer_email, co_borrower_email, 
                               approval_specialist_email, approval_specialist_first_name, approval_specialist_last_name):
    return hubspot.send_vpal_incomplete_email(buying_agent_email, customer_first_name, customer_email,
                                              co_borrower_email, approval_specialist_email, approval_specialist_first_name,
                                              approval_specialist_last_name)


def send_vpal_suspended_email(customer_email, customer_first_name, cc_email_list: List[str], loan_advisor_first_name: str = None,
                              loan_advisor_last_name: str = None, loan_advisor_call_link: str = None, loan_advisor_phone: str = None,
                              loan_advisor_email: str = None, approval_specialist_email: str = None, approval_specialist_first_name: str = None, 
                              approval_specialist_last_name: str = None):
    return hubspot.send_vpal_suspended_email(customer_email, customer_first_name, cc_email_list, loan_advisor_first_name, loan_advisor_last_name,
                                             loan_advisor_call_link, loan_advisor_phone, loan_advisor_email, 
                                             approval_specialist_email, approval_specialist_first_name, approval_specialist_last_name)


def send_vpal_ready_for_review_email(customer_first_name, customer_email, co_borrower_email, buying_agent_email, 
                                     approval_specialist_email, approval_specialist_first_name, approval_specialist_last_name):
    return hubspot.send_vpal_ready_for_review_email(customer_first_name, customer_email,
                                              co_borrower_email, buying_agent_email, approval_specialist_email, 
                                              approval_specialist_first_name, approval_specialist_last_name)
    
def send_apex_site_pre_account_email(customer_email, customer_first_name, partner_name, resume_link, buying_agent_name=None, buying_agent_email=None):
    # On this email, we want to pass back the agent name if there ends up being a missing partner name
    if buying_agent_name is None:
        buying_agent_name = DEFAULT_AGENT_NAME
    if partner_name is None:
        partner_name = buying_agent_name
    return hubspot.send_apex_site_pre_account_email(customer_email, customer_first_name, partner_name, resume_link, buying_agent_email)

def send_vpal_ready_for_review_follow_up(customer_first_name, customer_last_name, customer_email, co_borrower_email: str = None, buying_agent_email: str = None):
    return hubspot.send_vpal_ready_for_review_follow_up(customer_first_name, customer_last_name, customer_email, co_borrower_email, buying_agent_email)

def send_new_customer_partner_email(customer_name, customer_email, customer_phone, home_buying_stage, home_buying_location,
                                    current_home_address, partner_name, partner_email):
    return hubspot.send_new_customer_partner_email(customer_name, customer_email, customer_phone, home_buying_stage, home_buying_location,
                                                   current_home_address, partner_name, partner_email)

def send_application_complete_email(customer_email, customer_first_name, agent_email, 
                                    approval_specialist_first_name, approval_specialist_last_name, approval_specialist_email, loan_advisor_first_name, loan_advisor_last_name):
    return hubspot.send_application_complete_email(customer_email, customer_first_name, agent_email, 
                                                   approval_specialist_first_name, approval_specialist_last_name, approval_specialist_email, loan_advisor_first_name, loan_advisor_last_name)
