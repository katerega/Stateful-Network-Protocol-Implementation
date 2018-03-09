# StatefulNetworkProtocolImplementation

Implementation of a server for a simple stateful network protocol.

WAR: A Card game
Hearthstone: Heroes of Warcraft is a cross-platform online card game with “war” in the title. No matter whether using a Mac, PC, iOS, or Android device, anyone can play the game with anyone else. The original card game war, however, is much simpler than that game (although probably not more popular). For this assignment, we will be programming a cross-platform implementation of the “war” card game server. If you implement the protocol correctly, your code will be able to communicate with any other student’s code regardless of the choice of language.

WAR: The simplified rules
The simplified rules for our version of war are as follows: the dealer (server) deals half of the deck, at random, to the two players (clients). Each player “turns over” (sends) one of their cards to the server, and the server responds to each player “win” “lose” or “draw.” Unlike normal war (as this class is about network programming not video game programming), in the event of a tie neither player receives a “point” and play simply moves on to the next round. After all of the cards have been used, play stops and each client knows (based on the number of points they received) whether they won or they lost. Once each player has received the results of 26 rounds, they disconnect.

WAR: the network protocol
Parallel to the simplified rules, the WAR protocol is as follows. A war server listens for new TCP connections on a given port. It waits until two clients have connected to that port. Once both have connected, the clients send a message containing the “want game” command. If both clients do this correctly, the server responds with a message containing the “game start” command, with a payload containing the list of cards dealt to that client.

After each client has received their half of the deck, the clients send messages including the “play card” message, and set the payload to their chosen card. After the server has received a “play card” message from both clients, it will respond with a “play result” message to both clients, telling each one whether they won or lost. This process continues until each player has sent all of their cards and received all of their play results; after receiving the last play result, the clients disconnect; after sending the last play result, the server also disconnects.

For War v.1, your server and client only need to play one game, and then exit.

This project implements server serving multiple requests simultaneously.
