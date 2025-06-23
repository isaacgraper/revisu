from locust import HttpUser, task, between

class FastAPIUser(HttpUser):
    host = "http://localhost:8000"
    wait_time = between(1, 2)

    @task
    def process_file_endpoint(self):
        endpoint = "/files/process"

        file_content = """
            Bitcoin: A Peer-to-Peer Electronic Cash System

            Satoshi Nakamoto
            satoshin@gmx.com
            www.bitcoin.org

            Abstract. A purely peer-to-peer version of electronic cash would allow online
            payments to be sent directly from one party to another without going through a
            financial institution. Digital signatures provide part of the solution, but the main
            benefits are lost if a trusted third party is still required to prevent double-spending.
            We propose a solution to the double-spending problem using a peer-to-peer network.
            The network timestamps transactions by hashing them into an ongoing chain of
            hash-based proof-of-work, forming a record that cannot be changed without redoing
            the proof-of-work. The longest chain not only serves as proof of the sequence of
            events witnessed, but proof that it came from the largest pool of CPU power. As
            long as a majority of CPU power is controlled by nodes that are not cooperating to
            attack the network, they'll generate the longest chain and outpace attackers. The
            network itself requires minimal structure. Messages are broadcast on a best effort
            basis, and nodes can leave and rejoin the network at will, accepting the longest
            proof-of-work chain as proof of what happened while they were gone.
        """

        files = {'file': ('test_locust_file.txt', file_content, 'text/plain')}
        data = {'file_type': 'txt'}

        response = self.client.post(endpoint, files=files, data=data)

        if response.status_code == 200:
            print(f"Request {endpoint} successful: {response.json()}")
        else:
            print(f"Request {endpoint} failed with status {response.status_code}: {response.text}")
