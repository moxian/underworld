from gameengine import celldefs  # pylint: disable=import-error
import time
import sys
import argparse
import curses


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage()
        sys.stderr.write("replay plugin error: " + message + "\n")
        sys.exit(2)


class VizualizerCursesPlugin:
    """
    plugin to show game progress inside a console
    """
    def __init__(self, game, args):
        """
            Initialize a visualizer with an instance of Game.
            sets onTurnEnd binding
        """
        parser = ArgumentParser(prog="")
        parser.add_argument("--turn-time", "-t",
                            type=float,
                            help="delay between turns in seconds(%(default)f)",
                            default=0.1)
        self._options = parser.parse_args(args.split())
        self.turn_time = self._options.turn_time

        self.game = game
        self.game.onTurnEnd = self._turn_end
        self.curses_scr = None
        self.win_field = None
        self.win_players = None
        self.win_log = None
        self.player_colors = {}
        self._curses_init(game)

    def _curses_init(self, game):
        "initialize curses library and several windows"

        self.curses_scr = curses.initscr()
        field_height, field_width = game.SizeY+1, game.SizeX+1
        cur_y = 0

        self.win_field = curses.newwin(field_height, field_width, cur_y, 0)
        cur_y += field_height
        self.win_players = curses.newwin(len(game.players)+1, 80, cur_y, 0)
        cur_y += len(game.players) + 1
        self.win_log = curses.newwin(2, 10, cur_y, 0)

        curses.start_color()
        # I don't care what those colors are exactly. Just init them
        for i in range(1, 8):
            curses.init_pair(i, i, 0)
        self.player_colors = {
            -1: 1,
            0: 2,
            1: 3,
            2: 4,
            3: 5
        }
        return

    def __del__(self):
        # __del__'s black magic is not particularly nice, but accidentally
        # leaving user console messed up is even worse
        try:
            if self.curses_scr is not None:
                curses.endwin()
        except AttributeError:
            pass

    def show_field(self):
        " draw game field in console "
        for row_no, row in enumerate(self.game.field):
            for col_no, cell in enumerate(row):
                letter = '?'
                color = 0
                if cell is None:
                    letter = '.'
                else:
                    # gives awkward results if both class and it's superclass are listed
                    letter_mapping = {
                        celldefs.Castle: 'C',
                        celldefs.Barracks: 'B',
                        celldefs.Farm: 'F',
                        celldefs.Wall: '#',
                        celldefs.Warrior: 'w',
                    }
                    for cls, let in letter_mapping.items():
                        if isinstance(cell, cls):
                            letter = let
                if cell is None:
                    color = 0
                else:
                    color = self.player_colors.get(cell.owner, 0)

                color_attr = curses.color_pair(color)
                self.win_field.addch(row_no, col_no, letter, color_attr)

        self.win_field.refresh()
        return

    def show_player_stats(self):
        " draw players' statistics "
        # write headers
        name_len = max(len(player.name) for player in self.game.players)
        name_len = max(name_len, len("name"))

        name_start = 0
        money_start = name_len + 2
        self.win_players.addstr(0, name_start, "name")
        self.win_players.addstr(0, money_start, "money")

        # write players' info
        for player_no, player in enumerate(self.game.players):
            color = self.player_colors.get(player_no, 0)
            color_attr = curses.color_pair(color)

            player_y = player_no + 1
            self.win_players.addstr(player_y, name_start, player.name, color_attr)
            self.win_players.addstr(player_y, money_start, str(player.money), color_attr)

        self.win_players.refresh()
        return

    def _turn_end(self):
        " The event handler. "

        self.show_field()
        self.show_player_stats()

        # so that log at displays more-or-less readable
        # neither curses.setsyx(), nor curses.window.move() seem to work. At least on windows.
        self.win_log.addch(0, 0, '>')
        self.win_log.refresh()

        time.sleep(self.turn_time)
