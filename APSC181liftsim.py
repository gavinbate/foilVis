import pygame
from pygame.locals import *
import sys
import math
import random
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *

# Initialize pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 1000, 700
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (100, 149, 237)
RED = (255, 50, 50)
GRAY = (180, 180, 180)
DARK_BLUE = (0, 0, 128)
GREEN = (50, 205, 50)
PINK =  (255, 100, 170)
YELLOW = (255, 255, 0)

# Airfoil parameters
AIRFOIL_LENGTH = 5.0
AIRFOIL_WIDTH = 2
AIRFOIL_THICKNESS = 0.5
AIRFOIL_COLOR = (0.8, 0.8, 0.8, 0.5)

# Physics parameters
AIR_DENSITY = 1.225  # kg/m³
GRAVITY = 9.81  # m/s²
MASS = 10.0  # kg
LIFT_COEFFICIENT = 0.0  # Initial value
DRAG_COEFFICIENT = 0.02  # Initial value
REFERENCE_AREA = AIRFOIL_LENGTH * AIRFOIL_WIDTH  # Wing area in m²

# Camera parameters
camera_distance = 15.0
camera_rotation_x = 10
camera_rotation_y = 45

# Setup the display
screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
pygame.display.set_caption("3D Airfoil Dynamics Simulation")
clock = pygame.time.Clock()

# Fonts for UI
font = pygame.font.SysFont(None, 24)
title_font = pygame.font.SysFont(None, 36)

# Airfoil state
airfoil_angle = 0.0  # degrees
flow_velocity = 2.0  # m/s
vertical_velocity = 3.0  # m/s

# NACA airfoil parameters
thickness_ratio = 0.12  # Maximum thickness as fraction of chord
camber_ratio = 0.04    # Maximum camber as fraction of chord
camber_position = 0.4  # Position of maximum camber
n_points = 20          # Number of points for each surface

# Initialize OpenGL
def init_gl():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    # Light position and properties
    glLightfv(GL_LIGHT0, GL_POSITION, (5, 5, 10, 1))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))
    
    # Set perspective
    glMatrixMode(GL_PROJECTION)
    gluPerspective(45, (WIDTH / HEIGHT), 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)

# particle system 
class SimpleParticle:
    def __init__(self):
        self.x = random.uniform(-10, -5)
        self.y = random.uniform(-2, 2)
        self.z = random.uniform(-AIRFOIL_WIDTH/2, AIRFOIL_WIDTH/2)
        self.speed = flow_velocity
        self.lifetime = random.uniform(150, 250)
        self.max_lifetime = self.lifetime
        self.color = (0.5, 0.5, 0.5, 1.0)  # grey
        self.deflected = False
        self.deflection_strength = 0
    
    def update(self):
        # Basic movement
        self.x += self.speed * 0.05
        
        # Check if near the airfoil
        if not self.deflected and -2 <= self.x <= 3:
            # Calculate position relative to airfoil
            angle_rad = math.radians(airfoil_angle)
            rel_x = self.x * math.cos(angle_rad) + self.y * math.sin(angle_rad)
            rel_y = -self.x * math.sin(angle_rad) + self.y * math.cos(angle_rad)
            
            # Calculate distance to airfoil center
            if -AIRFOIL_LENGTH/2 <= rel_x <= AIRFOIL_LENGTH/2 and abs(rel_y) <= AIRFOIL_THICKNESS * 2:
                # Determine deflection direction based on position
                direction = -1 if rel_y > 0 else 1
                
                # Calculate deflection strength
                distance_factor = 1 - min(1, abs(rel_y) / (AIRFOIL_THICKNESS * 2))
                angle_factor = abs(math.sin(math.radians(airfoil_angle))) * 1.5 + 0.5
                
                self.deflection_strength = direction * distance_factor * angle_factor * 0.1
                self.deflected = True
                self.color = (1.0, 0.0, 0.7, 0.7)  # Change to pink when deflected


        
        # Apply deflection
        if self.deflected:
            self.y += self.deflection_strength
            self.deflection_strength *= 0.9995  # Fade out effect
        
        # Reduce lifetime
        self.lifetime -= 1.0
        
    def draw(self):
        alpha = self.lifetime / self.max_lifetime
        size = 0.1
        
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        
        # Disable lighting for particles
        glDisable(GL_LIGHTING)
        
        # Draw as a square facing the camera
        glColor4f(self.color[0], self.color[1], self.color[2], self.color[3] * alpha)
        glBegin(GL_QUADS)
        glVertex3f(-size, -size, 0)
        glVertex3f(size, -size, 0)
        glVertex3f(size, size, 0)
        glVertex3f(-size, size, 0)
        glEnd()
        
        glEnable(GL_LIGHTING)
        glPopMatrix()

# Particle system
particles = []
MAX_PARTICLES = 1000

def generate_particles():
    """Generate new particles"""
    if len(particles) < MAX_PARTICLES:
        for _ in range(3):
            particles.append(SimpleParticle())

def update_particles():
    """Update particles and remove dead ones"""
    for particle in particles[:]:
        particle.update()
        if particle.lifetime <= 0 or particle.x > 15 or abs(particle.y) > 10 or abs(particle.z) > 10:
            particles.remove(particle)

def draw_particles():
    """Draw all particles"""
    for particle in particles:
        particle.draw()

def generate_airfoil_profile():
    """Generate points for NACA 4-digit airfoil profile"""
    upper_surface = []
    lower_surface = []
    
    for i in range(n_points + 1):
        # Parameter along the chord (0 at leading edge, 1 at trailing edge)
        x = i / n_points
        
        # Mean camber line
        if x < camber_position:
            yc = camber_ratio * (x / camber_position**2) * (2 * camber_position - x)
        else:
            yc = camber_ratio * ((1 - x) / (1 - camber_position)**2) * (1 + x - 2 * camber_position)
        
        # Thickness distribution (symmetric about camber line)
        yt = thickness_ratio * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
        
        # Calculate the angle of the camber line
        if x < camber_position:
            dyc_dx = 2 * camber_ratio / camber_position**2 * (camber_position - x)
        else:
            dyc_dx = 2 * camber_ratio / (1 - camber_position)**2 * (camber_position - x)
        
        theta = math.atan(dyc_dx)
        
        # Upper and lower surface coordinates
        xu = x - yt * math.sin(theta)
        yu = yc + yt * math.cos(theta)
        
        xl = x + yt * math.sin(theta)
        yl = yc - yt * math.cos(theta)
        
        # Scale to airfoil dimensions
        xu = (xu - 0.5) * AIRFOIL_LENGTH
        yu = yu * AIRFOIL_LENGTH
        
        xl = (xl - 0.5) * AIRFOIL_LENGTH
        yl = yl * AIRFOIL_LENGTH
        
        upper_surface.append((xu, yu))
        lower_surface.append((xl, yl))
    
    return upper_surface, lower_surface

def draw_airfoil():
    """Draw the 3D airfoil"""
    upper_surface, lower_surface = generate_airfoil_profile()
    
    # Apply rotation for angle of attack
    glPushMatrix()
    glRotatef(airfoil_angle, 0, 0, 1)
    
    # Set material properties
    glColor4f(*AIRFOIL_COLOR)
    
    # Draw the airfoil surfaces
    half_width = AIRFOIL_WIDTH / 2
    
    # Top and bottom surfaces
    for surface_points in [upper_surface, lower_surface]:
        reverse = (surface_points == lower_surface)
        
        # Connect the points to form the surface
        glBegin(GL_TRIANGLE_STRIP)
        for i, (x, y) in enumerate(surface_points):
            # Front point
            glVertex3f(x, y, half_width)
            # Back point
            glVertex3f(x, y, -half_width)
            
            # Calculate normals for smooth shading
            if i < len(surface_points) - 1:
                next_x, next_y = surface_points[i+1]
                dx = next_x - x
                dy = next_y - y
                
                # Perpendicular vector (normal to the surface)
                if reverse:
                    normal = (-dy, dx, 0)
                else:
                    normal = (dy, -dx, 0)
                    
                # Normalize
                length = math.sqrt(normal[0]**2 + normal[1]**2)
                if length > 0:
                    normal = (normal[0]/length, normal[1]/length, normal[2])
                    
                glNormal3f(*normal)
        glEnd()
    
    # Draw the leading and trailing edges
    glBegin(GL_TRIANGLE_STRIP)
    for i in range(len(upper_surface)):
        # Upper surface point
        upper_x, upper_y = upper_surface[i]
        # Lower surface point
        lower_x, lower_y = lower_surface[i]
        
        # Leading edge - positive z side
        glVertex3f(upper_x, upper_y, half_width)
        glVertex3f(lower_x, lower_y, half_width)
    glEnd()
    
    glBegin(GL_TRIANGLE_STRIP)
    for i in range(len(upper_surface)):
        # Upper surface point
        upper_x, upper_y = upper_surface[i]
        # Lower surface point
        lower_x, lower_y = lower_surface[i]
        
        # Leading edge - negative z side
        glVertex3f(upper_x, upper_y, -half_width)
        glVertex3f(lower_x, lower_y, -half_width)
    glEnd()
    
    # Draw the wingtips (z-axis ends)
    glBegin(GL_TRIANGLE_STRIP)
    for i in range(len(upper_surface)):
        upper_x, upper_y = upper_surface[i]
        lower_x, lower_y = lower_surface[len(upper_surface) - 1 - i]
        
        # Positive z wingtip
        glVertex3f(upper_x, upper_y, half_width)
        glVertex3f(lower_x, lower_y, half_width)
    glEnd()
    
    glBegin(GL_TRIANGLE_STRIP)
    for i in range(len(upper_surface)):
        upper_x, upper_y = upper_surface[i]
        lower_x, lower_y = lower_surface[len(upper_surface) - 1 - i]
        
        # Negative z wingtip
        glVertex3f(upper_x, upper_y, -half_width)
        glVertex3f(lower_x, lower_y, -half_width)
    glEnd()
    
    # Draw coordinate axes at center of airfoil
    glDisable(GL_LIGHTING)
    
    # X-axis (red, chord direction)
    glBegin(GL_LINES)
    glColor3f(1, 0, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(2, 0, 0)
    glEnd()
    
    # Y-axis (green, lift direction)
    glBegin(GL_LINES)
    glColor3f(0, 1, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 2, 0)
    glEnd()
    
    # Z-axis (blue, span direction)
    glBegin(GL_LINES)
    glColor3f(0, 0, 1)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 0, 2)
    glEnd()
    
    glEnable(GL_LIGHTING)
    
    glPopMatrix()

def draw_force_vectors():
    """Draw force vectors representing lift and drag"""
    # Calculate forces
    lift_force, drag_force = calculate_forces()
    
    # Get the angle in radians
    angle_rad = math.radians(airfoil_angle)
    
    # Create a fresh matrix
    glPushMatrix()
    
    # Scale forces for visualization - MAKE MAGNITUDES MUCH MORE OBVIOUS
    # Use absolute values to ensure positive scaling
    lift_magnitude = abs(lift_force) 
    drag_magnitude = abs(drag_force)
    
    # Use a non-linear scaling to make differences more dramatic - square root function
    # This makes small changes more noticeable while preventing huge vectors
    lift_scale = 0.5 + 0.5 * math.sqrt(min(lift_magnitude / 5.0, 10.0))
    drag_scale = 0.5 + 0.5 * math.sqrt(min(drag_magnitude / 2.0, 10.0))
    drag_scale *= -1
    
    # Fixed scale for weight for comparison
    weight_scale = 1.0
    
    # Disable lighting for clearer vector display
    glDisable(GL_LIGHTING)
    
    # Draw LIFT vector (perpendicular to airfoil)
    glColor3f(0, 0.8, 0)  # Green
    
    # Calculate lift vector endpoint
    lift_x = -lift_scale * math.sin(angle_rad)
    lift_y = lift_scale * math.cos(angle_rad)
    
    # Draw lift vector line
    glLineWidth(4.0)  # Make lines thicker for better visibility
    glBegin(GL_LINES)
    glVertex3f(0, 0, 0)
    glVertex3f(lift_x, lift_y, 0)
    glEnd()
    glLineWidth(1.0)  # Reset line width
    
    # Add arrowhead to lift vector
    arrow_size = 0.3  # Fixed size for arrowhead
    # Angle for the lift vector (perpendicular to airfoil)
    lift_angle = angle_rad + math.pi/2
    
    glBegin(GL_TRIANGLES)
    glVertex3f(lift_x, lift_y, 0)
    glVertex3f(lift_x - arrow_size * math.cos(lift_angle - math.pi/6), 
               lift_y - arrow_size * math.sin(lift_angle - math.pi/6), 0)
    glVertex3f(lift_x - arrow_size * math.cos(lift_angle + math.pi/6), 
               lift_y - arrow_size * math.sin(lift_angle + math.pi/6), 0)
    glEnd()
    
    # Draw DRAG vector (parallel to relative wind)
    glColor3f(0.8, 0, 0)  # Red
    
    # Calculate drag vector endpoint (opposite to wind direction)
    drag_x = -drag_scale * math.cos(angle_rad)
    drag_y = -drag_scale * math.sin(angle_rad)
    
    # Draw drag vector line
    glLineWidth(4.0)  # Make lines thicker
    glBegin(GL_LINES)
    glVertex3f(0, 0, 0)
    glVertex3f(drag_x, drag_y, 0)
    glEnd()
    glLineWidth(1.0)  # Reset line width
    
    # Add arrowhead to drag vector
    # Angle for drag vector (opposite to wind direction)
    # Add arrowhead to drag vector
# For a vector pointing from origin to (drag_x, drag_y), the correct angle is:
    drag_angle = math.atan2(drag_y, drag_x)

    glBegin(GL_TRIANGLES)
    glVertex3f(drag_x, drag_y, 0)
    glVertex3f(drag_x - arrow_size * math.cos(drag_angle - math.pi/6), 
            drag_y - arrow_size * math.sin(drag_angle - math.pi/6), 0)
    glVertex3f(drag_x - arrow_size * math.cos(drag_angle + math.pi/6), 
            drag_y - arrow_size * math.sin(drag_angle + math.pi/6), 0)
    glEnd()
    
    # Draw WEIGHT vector (always straight down)
    glColor3f(0, 0, 0.8)  # Blue
    
    # Draw weight vector line
    glLineWidth(4.0)
    glBegin(GL_LINES)
    glVertex3f(0, 0, 0)
    glVertex3f(0, -weight_scale, 0)
    glEnd()
    glLineWidth(1.0)
    
    # Add arrowhead to weight vector
    glBegin(GL_TRIANGLES)
    glVertex3f(0, -weight_scale, 0)
    glVertex3f(arrow_size, -weight_scale + arrow_size, 0)
    glVertex3f(-arrow_size, -weight_scale + arrow_size, 0)
    glEnd()
    
    # Draw labels for vectors
    glRasterPos3f(lift_x + 0.1, lift_y + 0.1, 0)
    # Draw text label for lift (OpenGL doesn't have built-in text)
    
    glEnable(GL_LIGHTING)
    glPopMatrix()

def draw_grid():
    """Draw a reference grid"""
    glDisable(GL_LIGHTING)
    
    # Draw a grid on the XZ plane
    glColor3f(0.5, 0.5, 0.5)
    glBegin(GL_LINES)
    
    grid_size = 20
    grid_step = 1
    
    for i in range(-grid_size, grid_size + 1, grid_step):
        # X lines
        glVertex3f(i, -0.01, -grid_size)
        glVertex3f(i, -0.01, grid_size)
        
        # Z lines
        glVertex3f(-grid_size, -0.01, i)
        glVertex3f(grid_size, -0.01, i)
    
    glEnd()
    
    glEnable(GL_LIGHTING)

def calculate_forces():
    global LIFT_COEFFICIENT, DRAG_COEFFICIENT
    
    # Calculate angle of attack in radians
    alpha = math.radians(airfoil_angle)
    
    # lift coefficient model based on angle of attack
    if abs(airfoil_angle) < 15:
        # Normal range - standard lift curve
        LIFT_COEFFICIENT = 2.0 * math.pi * math.sin(alpha) * (1 - 0.3 * math.sin(alpha)**2)
    else:
        stall_factor = max(0, 1 - (abs(airfoil_angle) - 15) / 5)  # More dramatic drop-off
        LIFT_COEFFICIENT = 2.0 * math.pi * math.sin(alpha) * stall_factor * (1 - 0.3 * math.sin(alpha)**2)
    
    # Drag coefficient model (parasitic + induced) - amplified for visual effect
    DRAG_COEFFICIENT = 0.015 + (LIFT_COEFFICIENT**2) / (math.pi * 2.5)
    
    # Add extra drag at high angles of attack (stall region)
    if abs(airfoil_angle) > 15:
        stall_drag = 0.05 * (abs(airfoil_angle) - 15)  # Additional drag due to stall
        DRAG_COEFFICIENT += stall_drag
    
    # Calculate dynamic pressure
    dynamic_pressure = 0.5 * AIR_DENSITY * (flow_velocity**2)
    
    # Calculate lift and drag forces 
    lift_force = LIFT_COEFFICIENT * dynamic_pressure * REFERENCE_AREA  
    drag_force = DRAG_COEFFICIENT * dynamic_pressure * REFERENCE_AREA   
    
    return lift_force, drag_force

def draw_text_overlay():
    """Draw 2D text overlay with simulation data"""
    # Save the current OpenGL state
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    
    # Create all text surfaces using Pygame
    lift_force, drag_force = calculate_forces()
    angle_rad = math.radians(airfoil_angle)
    
    # Non-linear scaling as in the draw_force_vectors function
    lift_magnitude = abs(lift_force)
    drag_magnitude = abs(drag_force)
    lift_scale = 0.5 + 0.5 * math.sqrt(min(lift_magnitude / 5.0, 10.0))
    drag_scale = 0.5 + 0.5 * math.sqrt(min(drag_magnitude / 2.0, 10.0))
    
    # Force direction components
    lift_x = -lift_scale * math.sin(angle_rad)
    lift_y = lift_scale * math.cos(angle_rad)
    drag_x = -drag_scale * math.cos(angle_rad)
    drag_y = -drag_scale * math.sin(angle_rad)
    
    # Create a Pygame surface for our overlay
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    
    # Draw data panel background 
    panel_width = 280
    data_panel_rect = pygame.Rect(0, 0, panel_width, HEIGHT)  # Full height, starts at left edge
    pygame.draw.rect(overlay, (*PINK, 180), data_panel_rect)
    
    # Add title to the top left
    title_surface = title_font.render("APSC 181 Simulation", True, BLACK)
    overlay.blit(title_surface, (20, 20))  # Position at top left with margin
    
    # Add a divider line after the title
    pygame.draw.line(overlay, BLACK, (20, 55), (panel_width - 20, 55), 2)
    
    # Add all text elements - start below the divider
    texts = [
        f"Angle of Attack: {airfoil_angle:.1f}°",
        f"Flow Velocity: {flow_velocity:.1f} m/s",
        f"Lift Coefficient: {LIFT_COEFFICIENT:.3f}",
        f"Drag Coefficient: {DRAG_COEFFICIENT:.3f}",
        f"Lift Force: {lift_force:.2f} N",
        f"Drag Force: {drag_force:.2f} N",
        "",
        "Force Vectors:",
        f"Lift: ({lift_x/lift_scale:.2f}, {lift_y/lift_scale:.2f})",
        f"Drag: ({drag_x/drag_scale:.2f}, {drag_y/drag_scale:.2f})",
        f"Weight: (0.0, -1.0)",
        "",
        "Controls:",
        "up/down: angle of attack",
        "left/right: flow velocity",
        "W/S/A/D: Rotate camera",
        "Q/E: Zoom in/out",
        "R: Reset simulation"
    ]
    
    start_y = 70  # Start text below the divider line
    for i, text in enumerate(texts):
        text_surface = font.render(text, True, BLACK)
        overlay.blit(text_surface, (20, start_y + i * 22))  # Increased spacing for readability
    
    # Add force vector legend at the bottom of the panel
    legend_y = HEIGHT - 110  # Position from bottom
    
    # Legend title
    legend_title = font.render("Force Vector Legend:", True, BLACK)
    overlay.blit(legend_title, (20, legend_y))
    
    # Add a divider line above the legend
    pygame.draw.line(overlay, BLACK, (20, legend_y - 10), (panel_width - 20, legend_y - 10), 1)
    
    # Color samples and labels
    pygame.draw.rect(overlay, (0, 204, 0), (30, legend_y + 25, 15, 15))
    legend_lift = font.render(f"Lift: {lift_force:.1f} N", True, BLACK)
    overlay.blit(legend_lift, (55, legend_y + 25))
    
    pygame.draw.rect(overlay, (204, 0, 0), (30, legend_y + 50, 15, 15))
    legend_drag = font.render(f"Drag: {drag_force:.1f} N", True, BLACK)
    overlay.blit(legend_drag, (55, legend_y + 50))
    
    pygame.draw.rect(overlay, (0, 0, 204), (30, legend_y + 75, 15, 15))
    legend_weight = font.render(f"Weight: {MASS * GRAVITY:.1f} N", True, BLACK)
    overlay.blit(legend_weight, (55, legend_y + 75))
    
    # Switch to 2D orthographic projection with origin at top-left
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, WIDTH, HEIGHT, 0, -1, 1)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Convert the surface to raw data
    texture_data = pygame.image.tostring(overlay, "RGBA", 0)
    
    # Create and configure texture
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, WIDTH, HEIGHT, 0, GL_RGBA, 
                GL_UNSIGNED_BYTE, texture_data)
    
    # Draw the texture
    glEnable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    glColor4f(1.0, 1.0, 1.0, 1.0)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(0, 0)
    glTexCoord2f(1, 0); glVertex2f(WIDTH, 0)
    glTexCoord2f(1, 1); glVertex2f(WIDTH, HEIGHT)
    glTexCoord2f(0, 1); glVertex2f(0, HEIGHT)
    glEnd()
    
    # Clean up
    glDisable(GL_BLEND)
    glDisable(GL_TEXTURE_2D)
    glDeleteTextures([texture_id])
    
    # Restore OpenGL state
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)

def handle_events():
    """Process user input"""
    global airfoil_angle, flow_velocity, camera_rotation_x, camera_rotation_y, camera_distance
    
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
            
        if event.type == KEYDOWN:
            if event.key == K_r:  # Reset
                airfoil_angle = 0
                flow_velocity = 10.0
                camera_rotation_x = 30.0
                camera_rotation_y = 45.0
                camera_distance = 10.0
    
    keys = pygame.key.get_pressed()
    
    # Change angle of attack
    if keys[K_UP]:
        airfoil_angle = min(airfoil_angle + 0.5, 25.0)
    if keys[K_DOWN]:
        airfoil_angle = max(airfoil_angle - 0.5, -25.0)
        
    # Change flow velocity
    if keys[K_RIGHT]:
        flow_velocity = min(flow_velocity + 0.2, 30.0)
    if keys[K_LEFT]:
        flow_velocity = max(flow_velocity - 0.2, 2.0)
    
    # Camera controls
    if keys[K_w]:
        camera_rotation_x = min(camera_rotation_x + 1.0, 89.0)
    if keys[K_s]:
        camera_rotation_x = max(camera_rotation_x - 1.0, -89.0)
    if keys[K_a]:
        camera_rotation_y = (camera_rotation_y + 1.0) % 360.0
    if keys[K_d]:
        camera_rotation_y = (camera_rotation_y - 1.0) % 360.0
    if keys[K_q]:
        camera_distance = min(camera_distance + 0.2, 20.0)
    if keys[K_e]:
        camera_distance = max(camera_distance - 0.2, 3.0)

def setup_camera():
    """Position the camera based on rotation angles and distance"""
    # Convert spherical to Cartesian coordinates
    x = camera_distance * math.cos(math.radians(camera_rotation_x)) * math.sin(math.radians(camera_rotation_y))
    y = camera_distance * math.sin(math.radians(camera_rotation_x))
    z = camera_distance * math.cos(math.radians(camera_rotation_x)) * math.cos(math.radians(camera_rotation_y))
    
    # Look at the center of the scene
    glLoadIdentity()
    gluLookAt(x, y, z, 0, 0, 0, 0, 1, 0)

def main():
    """Main program loop"""
    init_gl()
    
    # Add a debug flag to print force data
    debug_counter = 0
    
    while True:
        # Process input
        handle_events()
        
        # Clear the screen and depth buffer
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Setup camera
        setup_camera()
        
        draw_text_overlay()

        # Draw elements
        draw_grid()
        draw_airfoil()
        draw_force_vectors()

        # Update and draw particles
        generate_particles()
        update_particles()
        draw_particles()
        
        # Draw 2D overlay
        draw_text_overlay()
        
        # Debug: Print force vector data 
        debug_counter += 1
        if debug_counter >= 60:
            debug_counter = 0
            lift_force, drag_force = calculate_forces()
            print(f"DEBUG - Angle: {airfoil_angle:.1f}°, Lift: {lift_force:.2f} N, Drag: {drag_force:.2f} N")
            print(f"DEBUG - Lift coefficient: {LIFT_COEFFICIENT:.3f}, Drag coefficient: {DRAG_COEFFICIENT:.3f}")
        
        
        # Update display
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()