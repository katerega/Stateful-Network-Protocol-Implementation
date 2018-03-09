"""
war card game client and server
"""
import asyncio
from collections import namedtuple
from enum import Enum
import logging
import random
import sys
import time
import functools


Game = namedtuple("Game", ["p1", "p2"])

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


def kill_game(game):
    """
    TODO: If either client sends a bad message, immediately nuke the game.
    """
    logging.debug("Killing game and closing connections")
    game.p1[1].close()
    game.p2[1].close()


def compare_cards(card1, card2):
    """
    TODO: Given an integer card representation, return -1 for card1 < card2,
    0 for card1 = card2, and 1 for card1 > card2
    """
    logging.debug("p1 card %d  p2 card %d", card1, card2)

    if card1 % 13 == card2 % 13:
        return 0
    elif card1 % 13 < card2 % 13:
        return -1
    return 1


def deal_cards():
    """
    TODO: Randomize a deck of cards (list of ints 0..51), and return two
    26 card "hands."
    """
    cards = []
    for i in range(0, 52):
        cards.append(i)
    random.shuffle(cards)
    return cards[:26], cards[26:]


async def send_result(comparison, p1_writer, p2_writer):
    """
    send results to the clients
    """
    if comparison == 0:
        resultp1 = Result.DRAW.value
        resultp2 = Result.DRAW.value
        logging.debug("............................Player 1 %s Player 2 %s", "DRAW", "DRAW")

    elif comparison == -1:
        resultp1 = Result.LOSE.value
        resultp2 = Result.WIN.value
        logging.debug("............................Player 1 %s Player 2 %s", "LOSE", "WIN")

    elif comparison == 1:
        resultp1 = Result.WIN.value
        resultp2 = Result.LOSE.value
        logging.debug("............................Player 1 %s Player 2 %s", "WIN", "LOSE")

    p1_writer.write(bytes([Command.PLAYRESULT.value, resultp1]))
    p2_writer.write(bytes([Command.PLAYRESULT.value, resultp2]))


async def handle_connection(reader, writer, players_waiting):
    """
    Handler for connections to server
    """
    logging.debug("handle_connection")
    players_waiting.append((reader, writer))

    logging.debug("Players connected %d ", len(players_waiting))

    if len(players_waiting) == 2:
        new_game = Game(players_waiting[0], players_waiting[1])
        players_waiting.clear()

        logging.debug("Start game")
        await play_game(new_game)
        return


async def play_game(game):
    """
    Game handler- 2 clients playing game
    """
    logging.debug("In play_game")
    p1_reader = game.p1[0]
    p2_reader = game.p2[0]
    p1_writer = game.p1[1]
    p2_writer = game.p2[1]

    try:
        print("players", p1_reader, p2_reader)
        p1_command = await p1_reader.readexactly(2)
        p2_command = await p2_reader.readexactly(2)

        logging.debug("*******  p1_command   ****** %d", p1_command[0])
        logging.debug("*******  p2_command   ****** %d", p2_command[0])
        logging.debug("*******  p1_payload   ****** %d", p1_command[1])
        logging.debug("*******  p2_payload   ****** %d", p2_command[1])

        if p1_command[0] != Command.WANTGAME.value or \
            p2_command[0] != Command.WANTGAME.value or\
            p1_command[1] != 0 or p2_command[1] != 0:
            logging.debug("Incorrect message. Disconnect clients")
            kill_game(game)
            return 0

        p1cards, p2cards = deal_cards()

        p1cards.insert(0, Command.GAMESTART.value)
        p2cards.insert(0, Command.GAMESTART.value)

        p1_writer.write(bytes(p1cards))
        p2_writer.write(bytes(p2cards))

        count = 0
        while count < 26:
            p1_card = await p1_reader.readexactly(2)
            p2_card = await p2_reader.readexactly(2)

            if p1_card[0] == Command.PLAYCARD.value and \
                p2_card[0] == Command.PLAYCARD.value and \
                p1_card[1] in p1cards and p2_card[1] in p2cards:

                p1cards.remove(p1_card[1])
                p2cards.remove(p2_card[1])
            else:
                kill_game(game)
                return 0

            comparison = compare_cards(p1_card[1], p2_card[1])
            await send_result(comparison, p1_writer, p2_writer)
            count += 1

        logging.debug("Game over")
        kill_game(game)

    except ConnectionResetError:
        logging.error("ConnectionResetError")
        kill_game(game)
        return 0
    except asyncio.streams.IncompleteReadError:
        logging.error("asyncio.streams.IncompleteReadError")
        kill_game(game)
        return 0
    except OSError:
        logging.error("OSError")
        kill_game(game)
        return 0


def serve_game(host, port):
    """
    TODO: Open a socket for listening for new connections on host:port, and
    perform the war protocol to serve a game of war between each client.
    This function should run forever, continually serving clients.
    """
    start = time.time()
    loop = asyncio.get_event_loop()
    players = []
    my_handler = functools.partial(handle_connection, players_waiting=players)
    coro = asyncio.start_server(my_handler, host, port, loop=loop)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # Close the server
        logging.debug("Closing the server")
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()
        end = time.time()
        logging.debug("Total time: %d", (end - start))


async def limit_client(host, port, loop, sem):
    """
    Limit the number of clients currently executing.
    You do not need to change this function.
    """
    async with sem:
        return await client(host, port, loop)


def readexactly(sock, numbytes):
    """
    Accumulate exactly `numbytes` from `sock` and return those. If EOF is found
    before numbytes have been received, be sure to account for that here or in
    the caller.
    """
    bytes_received = b""
    count = 0
    while count < numbytes:
        byte = sock.recv(1)
        if byte:
            count += 1
            bytes_received += byte
        else:
            raise asyncio.streams.IncompleteReadError(bytes_received, numbytes-count)

    return bytes_received


async def client(host, port, loop):
    """
    Run an individual client on a given event loop.
    You do not need to change this function.
    """
    try:
        reader, writer = await asyncio.open_connection(host, port, loop=loop)
        # send want game
        writer.write(b"\0\0")
        card_msg = await reader.readexactly(27)
        myscore = 0
        for card in card_msg[1:]:
            writer.write(bytes([Command.PLAYCARD.value, card]))
            result = await reader.readexactly(2)
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
