import requests


EXAMPLE_CONDITION_ASSIGNMENT_LIST = {
    "type": "AND",
    "items": [
        {
            "type": "AND",
            "items": [
                {
                    "type": "COND",
                    "field": "endDate",
                    "op": "GE",
                    "param": "2025-07-31T22:00:00.000Z"
                },
                {
                    "type": "COND",
                    "field": "endDate",
                    "op": "LE",
                    "param": "2025-12-31T21:59:59.999Z"
                }
            ]
        },
        {
            "type": "AND",
            "items": [
                {
                    "type": "COND",
                    "field": "startDate",
                    "op": "GE",
                    "param": "2000-12-31T23:00:00.000Z"
                },
                {
                    "type": "COND",
                    "field": "startDate",
                    "op": "LE",
                    "param": "2025-08-08T21:59:59.999Z"
                }
            ]
        },
        {
            "type": "COND",
            "field": "isDeleted",
            "op": "EQ",
            "param": [
                0
            ]
        }
    ]
}

EXAMPLE_WHAT_ASSIGNMENT_LIST = {
    "uid": 1,
    "createdDateTime": 1,
    "versionId": 1,
    "name": 1,
    "Candidate": {
        "fullName": 1,
        "candidateOuid": 1
    },
    "Customer": {
        "relation": 1,
        "relationId": 1
    },
    "startDate": 1,
    "endDate": 1
}

EXAMPLE_SORT_ASSIGNMENT_LIST = {
    "startDate": "DESC"
}


class OTYSAPIError(Exception):
    def __init__(self, message, error_code):
        super().__init__(f'{message} (error code: {error_code})')


class OTYSAPI:
    """
    use as context manager:

    with OTYSAPI(api_key) as api:
        api.get_assignment_list()

    docs: https://www.otys.com/wp-content/uploads/2025/01/Manual-OTYS-web-services-OWS.pdf
    list with all services: https://ows.otys.nl/info/
    available methods:
    - getListEx
    - add
    - update
    - delete
    - getDetail
    most services provide a maximum of 200 results per request
    there is a maximum of 350 requests per minute per API key, this issubject to change
    """

    def __init__(self, api_key):
        # a single session is created which will be re-used. This session is maximum valid for 14 hours
        self._api_key = api_key
        self.session_id = None  # set during __enter__
        self.url = "https://otys.otysapp.com/jservice.php"

    def __enter__(self):
        self.session_id = self._get_session_id(self._api_key)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._logout(self.session_id)

    def _raise_for_status(self, response):
        # when an error occurs, the backend still sends back status_code 200, so normal reponse.raise_for_status does not work
        response_json = response.json()
        if 'error' in response_json:
            raise OTYSAPIError(response_json['error']['message'], response_json['error']['code'])

    def _get_session_id(self, api_key):
        """
        This session_id is valid for 14 hours!
        """

        payload = {
            "jsonrpc": "2.0",
            "method": "loginByUid",
            "params": [
                f"{api_key}"
            ],
            "id": 1
        }
        headers = {}

        response = requests.request("POST", self.url, headers=headers, json=payload)
        self._raise_for_status(response)
        return response.json()['result']

    def _logout(self, session_id):
        payload = {
            "jsonrpc": "2.0",
            "method": "logout",
            "params": [
            f"{session_id}"
            ],
            "id": 1
        }
        headers = {}
        response = requests.request("POST", self.url, headers=headers, json=payload)
        self._raise_for_status(response)
        return response.json()['result']

    def get_assignment_list(self, limit=25, offset=0, condition=None, what=None, sort=None):
        """docs: https://ows.otys.nl/info/detail.php?service=Otys.Services.AssignmentService"""

        if sort is None:
            sort = {}

        method = "Otys.Services.AssignmentService.getListEx"
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": [
                f"{self.session_id}",
                {
                    # "what": what,  (optionally added later)
                    "limit": limit,
                    "offset": offset,
                    "getTotalCount": 1,
                    "sort": sort,
                    "excludeLimitCheck": True,
                    # "condition": condition,  (optionally added later)
                }
            ],
            "id": 1
        }
        
        if what is not None:
            payload['params'][1]['what'] = what
        if condition is not None:
            payload['params'][1]['condition'] = condition

        headers = {}

        response = requests.request("POST", self.url, headers=headers, json=payload)
        self._raise_for_status(response)
        return response.json()['result']

    def get_assignment_detail(self, assignment_id: str):

        method = "Otys.Services.AssignmentService.getDetail"
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": [
                f"{self.session_id}",
                f"{assignment_id}",
                {  # no what here
                    "uid": 1,
                    "createdDateTime": 1,
                    "versionId": 1,
                    "name": 1,
                    "Candidate": {
                        "fullName": 1,
                        "candidateOuid": 1
                    },
                    "Customer": {
                        "relation": 1,
                        "relationId": 1
                    },
                    "startDate": 1,
                    "endDate": 1
                }
            ],
            "id": 1
        }
        headers = {}

        response = requests.request("POST", self.url, headers=headers, json=payload)
        self._raise_for_status(response)
        print(response.json())

    def get_vacancy_list(self, limit=25, offset=0, condition=None, what=None, sort=None):
        """docs: https://ows.otys.nl/info/detail.php?service=Otys.Services.VacancyService"""

        if sort is None:
            sort = {}

        method = "Otys.Services.VacancyService.getListEx"
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": [
                f"{self.session_id}",
                {
                    # "what": what,  (optionally added later)
                    "limit": limit,
                    "offset": offset,
                    "getTotalCount": 1,
                    "sort": sort,
                    "excludeLimitCheck": True,
                    # "condition": condition,  (optionally added later)
                }
            ],
            "id": 1
        }

        if what is not None:
            payload['params'][1]['what'] = what
        if condition is not None:
            payload['params'][1]['condition'] = condition

        headers = {}

        response = requests.request("POST", self.url, headers=headers, json=payload)
        self._raise_for_status(response)
        return response.json()['result']

    def get_candidate_list(self, limit=25, offset=0, condition=None, what=None, sort=None):
        """docs: https://ows.otys.nl/info/detail.php?service=Otys.Services.CandidateService"""

        if sort is None:
            sort = {}

        method = "Otys.Services.CandidateService.getListEx"
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": [
                f"{self.session_id}",
                {
                    # "what": what,  (optionally added later)
                    "limit": limit,
                    "offset": offset,
                    "getTotalCount": 1,
                    "sort": sort,
                    "excludeLimitCheck": True,
                    # "condition": condition,  (optionally added later)
                }
            ],
            "id": 1
        }

        if what is not None:
            payload['params'][1]['what'] = what
        if condition is not None:
            payload['params'][1]['condition'] = condition

        headers = {}

        response = requests.request("POST", self.url, headers=headers, json=payload)
        self._raise_for_status(response)
        return response.json()['result']
    
    def get_candidate_detail(self, candidate_id: str):
        method = "Otys.Services.CandidateService.getDetail"
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": [
                f"{self.session_id}",
                f"{candidate_id}",
                {  # no what here
                    "uid": 1,
                    "Person": {
                        "firstName": 1,
                        "lastName": 1
                    },
                }
            ],
            "id": 1
        }
        headers = {}

        response = requests.request("POST", self.url, headers=headers, json=payload)
        self._raise_for_status(response)
        return response.json()

    def update_candidate_name(self, candidate_id: str, new_firstname: str):
        """Simple demonstrator for update functionality of API"""
        method = "Otys.Services.CandidateService.update"
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": [
                f"{self.session_id}",
                f"{candidate_id}",
                {  # no what here
                    "Person": {
                        "firstName": new_firstname,
                    },
                }
            ],
            "id": 1
        }
        headers = {}

        response = requests.request("POST", self.url, headers=headers, json=payload)
        self._raise_for_status(response)

    def create_candidate(self, firstname: str, lastname: str, email: str):
        """Simple demonstrator of create functionality over API"""
        method = "Otys.Services.CandidateService.add"
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": [
                f"{self.session_id}",
                {  # no what here
                    "Person": {
                        "firstName": firstname,
                        "lastName": lastname,
                        "emailPrimary": email, 
                    },
                }
            ],
            "id": 1
        }
        headers = {}

        response = requests.request("POST", self.url, headers=headers, json=payload)
        self._raise_for_status(response)
        return response.json()
    
    def delete_candidate(self, candidate_id: str):
        """Simple demonstrator of delete functionality over API"""
        method = "Otys.Services.CandidateService.delete"
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": [
                f"{self.session_id}",
                str(candidate_id),
            ],
            "id": 1
        }
        headers = {}

        response = requests.request("POST", self.url, headers=headers, json=payload)
        self._raise_for_status(response)
        return response.json()
