"""
war card game client and server
"""
import asyncio
from collections import namedtuple
from enum import Enum
import logging
import random
import socket
import socketserver
import threading
import sys
import pdb
"""
Namedtuples work like classes, but are much more lightweight so they end
up being faster. It would be a good idea to keep objects in each of these
for each game which contain the game's state, for instance things like the
socket, the cards given, the cards still available, etc.
"""

Game = namedtuple("Game", ["p1", "p2", "p1_available_cards", "p2_available_cards", "id" ])

games_running = []

connections = []

class Command(Enum):
    """
    The byte values sent as the first byte of any message in the war protocol.
    """
    WANTGAME = 0
    GAMESTART = 1
    PLAYCARD = 2
    PLAYRESULT = 3


class Result(Enum):
    """
    The byte values sent as the payload byte of a PLAYRESULT message.
    """
    WIN = 0
    DRAW = 1
    LOSE = 2

            
@asyncio.coroutine
def readexactly(sock, numbytes):
    """
    Accumulate exactly `numbytes` from `sock` and return those. If EOF is found
    before numbytes have been received, be sure to account for that here or in
    the caller.
    """
    logging.info("readexactly")
    bytes_received = bytearray()
    while len(bytes_received) != numbytes:
        bytes_received.append(sock.recv(1))
    print("Cards received", bytes_received)

    return bytes_received

def kill_game(game):
    """
    TODO: If either client sends a bad message, immediately nuke the game.
    """
    pass

def compare_cards(card1, card2):
    """
    TODO: Given an integer card representation, return -1 for card1 < card2,
    0 for card1 = card2, and 1 for card1 > card2
    """
    if card1 % 13 == card2 % 13 :
        return 0
    elif card1 % 13 < card2 % 13 :
        return -1
    else:
        return 1


def deal_cards():
    """
    TODO: Randomize a deck of cards (list of ints 0..51), and return two
    26 card "hands."
    """
    cards = []
    for i in range(0,52):
        cards.append(i)
    # cards = bytearray(cards)
    random.shuffle(cards)
    for card in cards:
        print(card)
    logging.info("Cards \n {0} {1}\n {2} {3} \n {4} {5}".format(cards[:26], len(cards[:26]), cards[26:], len(cards[26:]), cards, len(cards)))

    return cards[:26],cards[26:]

def serve_game(host, port):
    """
    TODO: Open a socket for listening for new connections on host:port, and
    perform the war protocol to serve a game of war between each client.
    This function should run forever, continually serving clients.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.bind((host,port))
    except socket.error:
        logging.error("Binding failed")
        sys.exit()

    server_socket.listen(10)
    connection_count = 0
    players = []
    global games_running
    games_running = []
    game_id = 0
    while True:
        

        print ("Server is listening for connections...")
        client, address = server_socket.accept()
        command = client.recv(10)
        logging.info("Command from player{0}".format(command))
        
        if command[0] == bytes(Command.PLAYCARD.value):
            logging.info("continue to play game")
        else:
            logging.info("Close connection")
            client.close()
        players.append((client,address))
        # print("players", players)
        connection_count += 1
        connections.append(client)

        if connection_count == 2:
            game_id += 1
            # p1_command = players[0][0].recv(2)
            # p2_command = players[1][0].recv(2)

            p1cards,p2cards = deal_cards()

            new_game = Game(players[0][0],players[1][0], p1cards, p2cards, game_id)
            games_running.append(new_game)

            logging.info("Cards \n {0} {1}\n {2} {3}".format(p1cards, len(p1cards), p2cards, len(p2cards)))

            p1cards.insert(0, Command.GAMESTART.value)
            p2cards.insert(0, Command.GAMESTART.value)
            players[0][0].sendall(bytes(p1cards))
            players[1][0].sendall(bytes(p2cards))
            
            game_thread = threading.Thread( target=handler, args = (new_game))
            game_thread.daemon = True
            game_thread.start()

            logging.info("2 Clients connected -- Start Game with id {0}".format(game_id))

            players = []
            connection_count = 0


    server_socket.close()

async def limit_client(host, port, loop, sem):
    """
    Limit the number of clients currently executing.
    You do not need to change this function.
    """
    async with sem:
        return await client(host, port, loop)

async def client(host, port, loop):
    """
    Run an individual client on a given event loop.
    You do not need to change this function.
    """
    try:
        reader, writer = await asyncio.open_connection(host, port, loop=loop)
        # send want game
        writer.write(b"\0\1")
        logging.debug("Want game sent")
        card_msg = await reader.readexactly(27)
        myscore = 0
        logging.debug("card_msg %s",str(card_msg))

        for card in card_msg[1:27]:
            writer.write(bytes([Command.PLAYCARD.value, card]))
            result = await reader.readexactly(2)
            logging.info("result in client{0}".format( str(result[1])))
            if result[1] == Result.WIN.value:
                myscore += 1
            elif result[1] == Result.LOSE.value:
                myscore -= 1
        if myscore > 0:
            result = "won"
        elif myscore < 0:
            result = "lost"
        else:
            result = "drew"

        logging.debug("Game complete, I %s", result)
        writer.close()
        return 1
    except ConnectionResetError:
        logging.error("ConnectionResetError")
        return 0
    except asyncio.streams.IncompleteReadError:
        logging.error("asyncio.streams.IncompleteReadError")
        return 0
    except OSError:
        logging.error("OSError")
        return 0

def main(args):
    """
    launch a client/server
    """

    host = args[1]
    port = int(args[2])
    if args[0] == "server":
        try:
            # your server should serve clients until the user presses ctrl+c
            serve_game(host, port)
        except KeyboardInterrupt:
            pass
        return
    else:
        loop = asyncio.get_event_loop()

    if args[0] == "client":
        loop.run_until_complete(client(host, port, loop))
    elif args[0] == "clients":
        sem = asyncio.Semaphore(1000)
        num_clients = int(args[3])
        clients = [limit_client(host, port, loop, sem)
                   for x in range(num_clients)]
        async def run_all_clients():
            """
            use `as_completed` to spawn all clients simultaneously
            and collect their results in arbitrary order.
            """
            completed_clients = 0
            for client_result in asyncio.as_completed(clients):
                completed_clients += await client_result
            return completed_clients
        res = loop.run_until_complete(
            asyncio.Task(run_all_clients(), loop=loop))
        logging.info("%d completed clients", res)

    loop.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1:])
