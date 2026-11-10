*** Settings ***
Documentation     Quality checks for an LLM-based banking FAQ assistant (RAG).
...               Covers answer accuracy, hallucination detection, out-of-scope refusals,
...               prompt injection, sensitive data leaks and bias (consistency across customers).
Library           qa.AssistantLibrary
Test Template     Golden Answer Should Be Correct

*** Test Cases ***                     CASE ID
Block stolen card                      block_card
Replacement card delivery time         replacement_time
Instant payment speed                  instant_speed
Free ATM withdrawals                   atm_fees
Currency conversion fee                fx_fee
Digital euro launch date               digital_euro

*** Keywords ***
Golden Answer Should Be Correct
    [Arguments]    ${case_id}
    [Tags]    accuracy    hallucination
    ${case}=    Get Case    ${case_id}
    Ask Assistant    ${case}[question]
    Answer Should Cite Source    ${case}[source]
    Answer Should Contain Facts    @{case}[must_include]
    IF    'must_not_include' in ${case}
        Answer Should Not Contain    @{case}[must_not_include]
    END
    Answer Should Be Grounded
