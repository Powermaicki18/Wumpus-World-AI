import random
from typing import Set, Tuple, List, Optional
from collections import deque


class WumpusWorld:
    """Entorno del Mundo del Wumpus"""

    def __init__(self, size=4):
        self.size = size
        self.grid = [[{'pit': False, 'wumpus': False, 'gold': False, 'visited': False}
                      for _ in range(size)] for _ in range(size)]
        self.agent_pos = (0, 0)
        self.agent_dir = 'ESTE'  # NORTE, SUR, ESTE, OESTE
        self.has_gold = False
        self.is_alive = True
        self.wumpus_alive = True
        self.has_arrow = True
        self.score = 0

        self._setup_world()

    def _setup_world(self):
        """Configura el mundo con Wumpus, pozos y oro"""
        # Colocar Wumpus (no en [0,0])
        while True:
            x, y = random.randint(0, self.size - 1), random.randint(0, self.size - 1)
            if (x, y) != (0, 0):
                self.grid[x][y]['wumpus'] = True
                self.wumpus_pos = (x, y)
                break

        # Colocar oro (no en [0,0])
        while True:
            x, y = random.randint(0, self.size - 1), random.randint(0, self.size - 1)
            if (x, y) != (0, 0) and not self.grid[x][y]['wumpus']:
                self.grid[x][y]['gold'] = True
                break

        # Colocar pozos (probabilidad 0.2, no en [0,0])
        for i in range(self.size):
            for j in range(self.size):
                if (i, j) != (0, 0) and random.random() < 0.2:
                    self.grid[i][j]['pit'] = True

    def get_percepts(self) -> dict:
        """Retorna las percepciones del agente en su posición actual"""
        x, y = self.agent_pos
        percepts = {
            'stench': False,
            'breeze': False,
            'glitter': False,
            'bump': False,
            'scream': False
        }

        # Detectar hedor (Wumpus adyacente)
        if self.wumpus_alive:
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.size and 0 <= ny < self.size:
                    if self.grid[nx][ny]['wumpus']:
                        percepts['stench'] = True

        # Detectar brisa (pozo adyacente)
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.size and 0 <= ny < self.size:
                if self.grid[nx][ny]['pit']:
                    percepts['breeze'] = True

        # Detectar brillo (oro en celda actual)
        if self.grid[x][y]['gold'] and not self.has_gold:
            percepts['glitter'] = True

        return percepts

    def move_forward(self) -> bool:
        """Mueve al agente hacia adelante"""
        x, y = self.agent_pos
        if self.agent_dir == 'NORTE':
            new_pos = (x, y + 1)
        elif self.agent_dir == 'SUR':
            new_pos = (x, y - 1)
        elif self.agent_dir == 'ESTE':
            new_pos = (x + 1, y)
        else:  # OESTE
            new_pos = (x - 1, y)

        # Verificar límites
        if not (0 <= new_pos[0] < self.size and 0 <= new_pos[1] < self.size):
            return False

        self.agent_pos = new_pos
        self.score -= 1

        # Verificar muerte
        x, y = self.agent_pos
        if self.grid[x][y]['pit'] or (self.grid[x][y]['wumpus'] and self.wumpus_alive):
            self.is_alive = False
            self.score -= 1000

        self.grid[x][y]['visited'] = True
        return True

    def turn_left(self):
        """Gira 90 grados a la izquierda"""
        dirs = ['NORTE', 'OESTE', 'SUR', 'ESTE']
        idx = dirs.index(self.agent_dir)
        self.agent_dir = dirs[(idx + 1) % 4]
        self.score -= 1

    def turn_right(self):
        """Gira 90 grados a la derecha"""
        dirs = ['NORTE', 'ESTE', 'SUR', 'OESTE']
        idx = dirs.index(self.agent_dir)
        self.agent_dir = dirs[(idx + 1) % 4]
        self.score -= 1

    def grab(self):
        """Recoge el oro si está presente"""
        x, y = self.agent_pos
        if self.grid[x][y]['gold']:
            self.has_gold = True
            self.grid[x][y]['gold'] = False
            self.score += 1000

    def shoot(self) -> bool:
        """Dispara la flecha"""
        if not self.has_arrow:
            return False

        self.has_arrow = False
        self.score -= 10

        # La flecha viaja en línea recta
        x, y = self.agent_pos
        dx, dy = {'NORTE': (0, 1), 'SUR': (0, -1), 'ESTE': (1, 0), 'OESTE': (-1, 0)}[self.agent_dir]

        while True:
            x, y = x + dx, y + dy
            if not (0 <= x < self.size and 0 <= y < self.size):
                break
            if self.grid[x][y]['wumpus'] and self.wumpus_alive:
                self.wumpus_alive = False
                return True

        return False


class IntelligentAgent:
    """Agente inteligente con razonamiento lógico"""

    def __init__(self, world_size=4):
        self.size = world_size
        self.kb = {  # Base de conocimiento
            'safe': {(0, 0)},  # Celdas seguras conocidas
            'visited': {(0, 0)},
            'wumpus_possible': set(),
            'pit_possible': set(),
            'has_gold': False,
            'wumpus_alive': True
        }
        self.path = [(0, 0)]
        self.plan = []

    def update_kb(self, pos: Tuple[int, int], percepts: dict):
        """Actualiza la base de conocimiento con nuevas percepciones"""
        x, y = pos
        self.kb['visited'].add(pos)

        # Obtener celdas adyacentes
        adjacent = self._get_adjacent(pos)

        if not percepts['stench'] and not percepts['breeze']:
            # Si no hay peligros, todas las adyacentes son seguras
            self.kb['safe'].update(adjacent)
        else:
            # Inferir ubicaciones posibles de peligros
            if percepts['stench'] and self.kb['wumpus_alive']:
                for adj in adjacent:
                    if adj not in self.kb['visited']:
                        self.kb['wumpus_possible'].add(adj)

            if percepts['breeze']:
                for adj in adjacent:
                    if adj not in self.kb['visited']:
                        self.kb['pit_possible'].add(adj)

            # Las celdas seguras son las que no son posibles peligros
            for adj in adjacent:
                if adj not in self.kb['wumpus_possible'] and adj not in self.kb['pit_possible']:
                    self.kb['safe'].add(adj)

    def _get_adjacent(self, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Retorna celdas adyacentes válidas"""
        x, y = pos
        adjacent = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.size and 0 <= ny < self.size:
                adjacent.append((nx, ny))
        return adjacent

    def choose_action(self, current_pos: Tuple[int, int], percepts: dict) -> str:
        """Elige la mejor acción basada en razonamiento lógico"""

        # Actualizar conocimiento
        self.update_kb(current_pos, percepts)

        # Si hay oro, recogerlo
        if percepts['glitter']:
            self.kb['has_gold'] = True
            return 'GRAB'

        # Si tenemos el oro, volver al inicio
        if self.kb['has_gold']:
            if current_pos == (0, 0):
                return 'CLIMB'
            # Planear ruta de regreso
            return self._plan_move_to((0, 0), current_pos)

        # Buscar celdas seguras no visitadas
        safe_unvisited = self.kb['safe'] - self.kb['visited']

        if safe_unvisited:
            # Moverse a la celda segura más cercana
            target = min(safe_unvisited, key=lambda p: abs(p[0] - current_pos[0]) + abs(p[1] - current_pos[1]))
            return self._plan_move_to(target, current_pos)

        # Si no hay celdas seguras, intentar explorar con cautela
        adjacent = self._get_adjacent(current_pos)
        for adj in adjacent:
            if adj not in self.kb['visited']:
                # Asumir riesgo calculado
                return self._plan_move_to(adj, current_pos)

        # Si no hay nada que hacer, volver al inicio
        return self._plan_move_to((0, 0), current_pos)

    def _plan_move_to(self, target: Tuple[int, int], current: Tuple[int, int]) -> str:
        """Planea movimiento hacia una celda objetivo"""
        dx = target[0] - current[0]
        dy = target[1] - current[1]

        if dx > 0:
            return 'MOVE_ESTE'
        elif dx < 0:
            return 'MOVE_OESTE'
        elif dy > 0:
            return 'MOVE_NORTE'
        elif dy < 0:
            return 'MOVE_SUR'

        return 'STAY'


def print_world(world: WumpusWorld, agent: IntelligentAgent):
    """Visualiza el mundo y el conocimiento del agente"""
    print("\n" + "=" * 50)
    print(f"Posición: {world.agent_pos} | Dirección: {world.agent_dir}")
    print(f"Puntuación: {world.score} | Oro: {world.has_gold} | Vivo: {world.is_alive}")
    print("=" * 50)

    # Imprimir cuadrícula
    for y in range(world.size - 1, -1, -1):
        row = ""
        for x in range(world.size):
            cell = "["

            # Contenido real (solo para visualización, el agente no lo ve)
            if world.grid[x][y]['wumpus']:
                cell += "W"
            elif world.grid[x][y]['pit']:
                cell += "P"
            elif world.grid[x][y]['gold']:
                cell += "G"
            else:
                cell += " "

            # Agente
            if (x, y) == world.agent_pos:
                cell += "A"
            else:
                cell += " "

            # Visitado
            if (x, y) in agent.kb['visited']:
                cell += "v"
            else:
                cell += " "

            cell += "]"
            row += cell

        print(f"{y} {row}")

    print("  " + "".join([f" {x}  " for x in range(world.size)]))
    print("\nLeyenda: W=Wumpus, P=Pozo, G=Oro, A=Agente, v=Visitado")


def run_game():
    """Ejecuta una partida completa"""
    world = WumpusWorld(size=4)
    agent = IntelligentAgent(world_size=4)

    print("🎮 BIENVENIDO AL MUNDO DEL WUMPUS 🎮")
    print_world(world, agent)

    max_steps = 100
    step = 0

    while world.is_alive and step < max_steps:
        percepts = world.get_percepts()

        print(f"\n--- Paso {step + 1} ---")
        print(f"Percepciones: {percepts}")

        # Agente decide acción
        action = agent.choose_action(world.agent_pos, percepts)
        print(f"Acción del agente: {action}")

        # Ejecutar acción
        if action == 'GRAB':
            world.grab()
        elif action == 'CLIMB':
            if world.agent_pos == (0, 0):
                print("\n🎉 ¡EL AGENTE ESCAPÓ CON EL ORO! 🎉")
                break
        elif action.startswith('MOVE_'):
            direction = action.split('_')[1]
            # Orientar al agente
            while world.agent_dir != direction:
                world.turn_right()
            # Moverse
            world.move_forward()

        print_world(world, agent)

        if not world.is_alive:
            print("\n💀 EL AGENTE HA MUERTO 💀")
            break

        step += 1
        input("Presiona ENTER para continuar...")

    print(f"\n{'=' * 50}")
    print(f"JUEGO TERMINADO")
    print(f"Puntuación final: {world.score}")
    print(f"Pasos totales: {step}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    run_game()