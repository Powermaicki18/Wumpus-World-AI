import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Set, Tuple, List, Dict
import random
from PIL import Image, ImageTk
import os


class WumpusWorld:
    """Entorno del Mundo del Wumpus"""

    def __init__(self, size=6):
        self.size = size
        self.grid = [[{'pit': False, 'wumpus': False, 'gold': False, 'visited': False}
                      for _ in range(size)] for _ in range(size)]
        self.agent_pos = (0, 0)
        self.agent_dir = 'ESTE'
        self.has_gold = False
        self.is_alive = True
        self.wumpus_alive = True
        self.has_arrow = True
        self.score = 0
        self.game_over = False

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

        if self.wumpus_alive:
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.size and 0 <= ny < self.size:
                    if self.grid[nx][ny]['wumpus']:
                        percepts['stench'] = True

        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.size and 0 <= ny < self.size:
                if self.grid[nx][ny]['pit']:
                    percepts['breeze'] = True

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
        else:
            new_pos = (x - 1, y)

        if not (0 <= new_pos[0] < self.size and 0 <= new_pos[1] < self.size):
            return False

        self.agent_pos = new_pos
        self.score -= 1

        x, y = self.agent_pos
        if self.grid[x][y]['pit'] or (self.grid[x][y]['wumpus'] and self.wumpus_alive):
            self.is_alive = False
            self.score -= 1000
            self.game_over = True

        self.grid[x][y]['visited'] = True
        return True

    def turn_left(self):
        dirs = ['NORTE', 'OESTE', 'SUR', 'ESTE']
        idx = dirs.index(self.agent_dir)
        self.agent_dir = dirs[(idx + 1) % 4]
        self.score -= 1

    def turn_right(self):
        dirs = ['NORTE', 'ESTE', 'SUR', 'OESTE']
        idx = dirs.index(self.agent_dir)
        self.agent_dir = dirs[(idx + 1) % 4]
        self.score -= 1

    def grab(self):
        x, y = self.agent_pos
        if self.grid[x][y]['gold']:
            self.has_gold = True
            self.grid[x][y]['gold'] = False
            self.score += 1000

    def climb(self):
        if self.agent_pos == (0, 0) and self.has_gold:
            self.game_over = True
            return True
        return False


class IntelligentAgent:
    """Agente inteligente con razonamiento lógico"""

    def __init__(self, world_size=6):
        self.size = world_size
        self.kb = {
            'safe': {(0, 0)},
            'visited': {(0, 0)},
            'wumpus_possible': set(),
            'pit_possible': set(),
            'has_gold': False,
            'wumpus_alive': True
        }

    def update_kb(self, pos: Tuple[int, int], percepts: dict):
        x, y = pos
        self.kb['visited'].add(pos)
        adjacent = self._get_adjacent(pos)

        if not percepts['stench'] and not percepts['breeze']:
            self.kb['safe'].update(adjacent)
        else:
            if percepts['stench'] and self.kb['wumpus_alive']:
                for adj in adjacent:
                    if adj not in self.kb['visited']:
                        self.kb['wumpus_possible'].add(adj)

            if percepts['breeze']:
                for adj in adjacent:
                    if adj not in self.kb['visited']:
                        self.kb['pit_possible'].add(adj)

            for adj in adjacent:
                if adj not in self.kb['wumpus_possible'] and adj not in self.kb['pit_possible']:
                    self.kb['safe'].add(adj)

    def _get_adjacent(self, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        x, y = pos
        adjacent = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.size and 0 <= ny < self.size:
                adjacent.append((nx, ny))
        return adjacent

    def choose_action(self, current_pos: Tuple[int, int], percepts: dict) -> str:
        self.update_kb(current_pos, percepts)

        if percepts['glitter']:
            self.kb['has_gold'] = True
            return 'GRAB'

        if self.kb['has_gold']:
            if current_pos == (0, 0):
                return 'CLIMB'
            return self._plan_move_to((0, 0), current_pos)

        safe_unvisited = self.kb['safe'] - self.kb['visited']

        if safe_unvisited:
            target = min(safe_unvisited, key=lambda p: abs(p[0] - current_pos[0]) + abs(p[1] - current_pos[1]))
            return self._plan_move_to(target, current_pos)

        adjacent = self._get_adjacent(current_pos)
        for adj in adjacent:
            if adj not in self.kb['visited']:
                return self._plan_move_to(adj, current_pos)

        return self._plan_move_to((0, 0), current_pos)

    def _plan_move_to(self, target: Tuple[int, int], current: Tuple[int, int]) -> str:
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


class WumpusGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎮 El Mundo del Wumpus - Agente Inteligente [6x6]")
        self.root.configure(bg='#2c3e50')

        self.world = WumpusWorld(size=6)
        self.agent = IntelligentAgent(world_size=6)

        self.cell_size = 80
        self.auto_play = False
        self.step_count = 0
        self.show_all = False  # Modo de visualización completa

        # Diccionario de imágenes personalizadas
        self.custom_images = {
            'wumpus': None,
            'agent': None,
            'gold': None,
            'pit': None,
            'breeze': None,
            'stench': None
        }

        self.setup_ui()
        self.update_display()

    def setup_ui(self):
        # Frame principal
        main_frame = tk.Frame(self.root, bg='#2c3e50')
        main_frame.pack(padx=20, pady=20)

        # Panel de información
        info_frame = tk.Frame(main_frame, bg='#34495e', relief=tk.RAISED, bd=2)
        info_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))

        self.info_label = tk.Label(info_frame, text="", font=('Arial', 11, 'bold'),
                                   bg='#34495e', fg='#ecf0f1', justify=tk.LEFT, padx=10, pady=10)
        self.info_label.pack()

        # Canvas para el tablero 6x6
        self.canvas = tk.Canvas(main_frame, width=self.cell_size * 6, height=self.cell_size * 6,
                                bg='#ecf0f1', highlightthickness=2, highlightbackground='#95a5a6')
        self.canvas.pack(pady=10)

        # Panel de controles
        control_frame = tk.Frame(main_frame, bg='#2c3e50')
        control_frame.pack(side=tk.TOP, pady=10)

        btn_style = {'font': ('Arial', 9, 'bold'), 'width': 13, 'height': 2}

        tk.Button(control_frame, text="▶️ Paso Manual", command=self.manual_step,
                  bg='#3498db', fg='white', **btn_style).grid(row=0, column=0, padx=5)

        self.auto_btn = tk.Button(control_frame, text="⚡ Auto Jugar", command=self.toggle_auto_play,
                                  bg='#2ecc71', fg='white', **btn_style)
        self.auto_btn.grid(row=0, column=1, padx=5)

        tk.Button(control_frame, text="🔄 Reiniciar", command=self.reset_game,
                  bg='#e74c3c', fg='white', **btn_style).grid(row=0, column=2, padx=5)

        # Botón de visualización completa
        self.view_btn = tk.Button(control_frame, text="👁️ Ver Todo", command=self.toggle_view_mode,
                                  bg='#9b59b6', fg='white', **btn_style)
        self.view_btn.grid(row=0, column=3, padx=5)

        # Panel de imágenes
        image_frame = tk.LabelFrame(main_frame, text="🖼️ Personalizar Imágenes",
                                    bg='#34495e', fg='#ecf0f1', font=('Arial', 10, 'bold'))
        image_frame.pack(side=tk.TOP, fill=tk.X, pady=10)

        image_buttons = [
            ('Wumpus', 'wumpus'), ('Agente', 'agent'), ('Oro', 'gold'),
            ('Pozo', 'pit'), ('Brisa', 'breeze'), ('Hedor', 'stench')
        ]

        for i, (label, key) in enumerate(image_buttons):
            btn = tk.Button(image_frame, text=f"🖼️ {label}",
                            command=lambda k=key: self.load_custom_image(k),
                            bg='#9b59b6', fg='white', font=('Arial', 9))
            btn.grid(row=0, column=i, padx=3, pady=5)

    def load_custom_image(self, image_key):
        """Carga una imagen personalizada"""
        file_path = filedialog.askopenfilename(
            title=f"Seleccionar imagen para {image_key}",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )

        if file_path:
            try:
                img = Image.open(file_path)
                img = img.resize((35, 35), Image.Resampling.LANCZOS)
                self.custom_images[image_key] = ImageTk.PhotoImage(img)
                self.update_display()
                messagebox.showinfo("✅ Éxito", f"Imagen de {image_key} cargada correctamente")
            except Exception as e:
                messagebox.showerror("❌ Error", f"No se pudo cargar la imagen: {e}")

    def draw_cell(self, x, y):
        """Dibuja una celda del tablero"""
        cx = x * self.cell_size
        cy = (5 - y) * self.cell_size  # Invertir Y para tablero 6x6

        # Fondo de celda
        if (x, y) in self.agent.kb['visited']:
            color = '#bdc3c7'
        elif (x, y) in self.agent.kb['safe']:
            color = '#d5f4e6'
        else:
            color = '#ecf0f1'

        self.canvas.create_rectangle(cx, cy, cx + self.cell_size, cy + self.cell_size,
                                     fill=color, outline='#7f8c8d', width=2)

        # Coordenadas
        self.canvas.create_text(cx + 10, cy + 10, text=f"({x},{y})",
                                font=('Arial', 7), fill='#7f8c8d')

        # Percepciones
        percepts = self.world.get_percepts() if (x, y) == self.world.agent_pos else None

        # Modo de visualización: mostrar todo si show_all está activo
        show_content = self.show_all or (x, y) in self.agent.kb['visited'] or (x, y) == self.world.agent_pos

        if show_content:
            # Mostrar peligros reales en modo "Ver Todo"
            if self.show_all:
                if self.world.grid[x][y]['pit']:
                    self.draw_element(cx, cy, 'pit', '🕳️', offset=(40, 40), size=18)
                if self.world.grid[x][y]['wumpus'] and self.world.wumpus_alive:
                    self.draw_element(cx, cy, 'wumpus', '👹', offset=(40, 40), size=18)

            # Percepciones solo en la posición actual
            if percepts and percepts['breeze']:
                self.draw_element(cx, cy, 'breeze', '💨', offset=(15, 60), size=14)

            if percepts and percepts['stench']:
                self.draw_element(cx, cy, 'stench', '💀', offset=(60, 60), size=14)

            if self.world.grid[x][y]['gold'] and not self.world.has_gold:
                self.draw_element(cx, cy, 'gold', '💰', offset=(40, 40), size=20)

        # Agente siempre visible
        if (x, y) == self.world.agent_pos:
            direction_arrows = {'NORTE': '⬆️', 'SUR': '⬇️', 'ESTE': '➡️', 'OESTE': '⬅️'}
            agent_symbol = direction_arrows[self.world.agent_dir]
            self.draw_element(cx, cy, 'agent', agent_symbol, offset=(40, 20), size=18)

    def draw_element(self, cx, cy, key, default_emoji, offset=(40, 40), size=18):
        """Dibuja un elemento (imagen personalizada o emoji)"""
        if self.custom_images[key]:
            self.canvas.create_image(cx + offset[0], cy + offset[1],
                                     image=self.custom_images[key])
        else:
            self.canvas.create_text(cx + offset[0], cy + offset[1],
                                    text=default_emoji, font=('Arial', size))

    def update_display(self):
        """Actualiza la visualización del tablero"""
        self.canvas.delete("all")

        # Dibujar todas las celdas del tablero 6x6
        for x in range(6):
            for y in range(6):
                self.draw_cell(x, y)

        # Actualizar información
        percepts = self.world.get_percepts()
        percept_str = ", ".join([k.upper() for k, v in percepts.items() if v])

        info_text = f"📍 Posición: {self.world.agent_pos} | 🧭 Dirección: {self.world.agent_dir}\n"
        info_text += f"🎯 Puntuación: {self.world.score} | 💰 Oro: {'✅' if self.world.has_gold else '❌'} | "
        info_text += f"❤️ Vivo: {'✅' if self.world.is_alive else '❌'}\n"
        info_text += f"👁️ Percepciones: {percept_str if percept_str else 'Ninguna'} | 📊 Pasos: {self.step_count}"
        if self.show_all:
            info_text += " | 🔍 Modo: VER TODO ACTIVADO"

        self.info_label.config(text=info_text)

    def manual_step(self):
        """Ejecuta un paso manual del agente"""
        if self.world.game_over:
            return

        percepts = self.world.get_percepts()
        action = self.agent.choose_action(self.world.agent_pos, percepts)

        self.execute_action(action)
        self.step_count += 1
        self.update_display()

        self.check_game_over()

    def execute_action(self, action):
        """Ejecuta una acción del agente"""
        if action == 'GRAB':
            self.world.grab()
        elif action == 'CLIMB':
            self.world.climb()
        elif action.startswith('MOVE_'):
            direction = action.split('_')[1]
            while self.world.agent_dir != direction:
                self.world.turn_right()
            self.world.move_forward()

    def toggle_auto_play(self):
        """Activa/desactiva el modo auto-jugar"""
        self.auto_play = not self.auto_play
        if self.auto_play:
            self.auto_btn.config(text="⏸️ Pausar", bg='#f39c12')
            self.auto_step()
        else:
            self.auto_btn.config(text="⚡ Auto Jugar", bg='#2ecc71')

    def auto_step(self):
        """Ejecuta pasos automáticamente"""
        if self.auto_play and not self.world.game_over:
            self.manual_step()
            self.root.after(500, self.auto_step)
        else:
            self.auto_play = False
            self.auto_btn.config(text="⚡ Auto Jugar", bg='#2ecc71')

    def toggle_view_mode(self):
        """Alterna entre modo normal y ver todo el tablero"""
        self.show_all = not self.show_all
        if self.show_all:
            self.view_btn.config(text="🙈 Ocultar", bg='#e67e22')
        else:
            self.view_btn.config(text="👁️ Ver Todo", bg='#9b59b6')
        self.update_display()

    def check_game_over(self):
        """Verifica si el juego ha terminado"""
        if self.world.game_over:
            if self.world.has_gold and self.world.agent_pos == (0, 0):
                messagebox.showinfo("🎉 ¡Victoria!",
                                    f"¡El agente escapó con el oro!\n\nPuntuación: {self.world.score}\nPasos: {self.step_count}")
            elif not self.world.is_alive:
                messagebox.showerror("💀 Game Over",
                                     f"El agente ha muerto...\n\nPuntuación: {self.world.score}\nPasos: {self.step_count}")

    def reset_game(self):
        """Reinicia el juego"""
        self.world = WumpusWorld(size=6)
        self.agent = IntelligentAgent(world_size=6)
        self.auto_play = False
        self.step_count = 0
        self.show_all = False
        self.auto_btn.config(text="⚡ Auto Jugar", bg='#2ecc71')
        self.view_btn.config(text="👁️ Ver Todo", bg='#9b59b6')
        self.update_display()


def main():
    root = tk.Tk()
    app = WumpusGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()