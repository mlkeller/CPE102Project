import actions
import entities
import image_store
import occ_grid
import ordered_list
import math
import point
import pygame
import random

BLOB_RATE_SCALE = 4
BLOB_ANIMATION_RATE_SCALE = 50
BLOB_ANIMATION_MIN = 1
BLOB_ANIMATION_MAX = 3

ORE_CORRUPT_MIN = 20000
ORE_CORRUPT_MAX = 30000

QUAKE_STEPS = 10
QUAKE_DURATION = 1100
QUAKE_ANIMATION_RATE = 100

VEIN_SPAWN_DELAY = 500
VEIN_RATE_MIN = 8000
VEIN_RATE_MAX = 17000


class WorldModel:
   def __init__(self, num_rows, num_cols, background):
      self.background = occ_grid.Grid(num_cols, num_rows, background)
      self.num_rows = num_rows
      self.num_cols = num_cols
      self.occupancy = occ_grid.Grid(num_cols, num_rows, None)
      self.entities = []
      self.action_queue = ordered_list.OrderedList()


   def sign(self, x):
      if x < 0:
         return -1
      elif x > 0:
         return 1
      else:
         return 0

   def adjacent(self, pt1, pt2):
      return ((pt1.x == pt2.x and abs(pt1.y - pt2.y) == 1) or
         (pt1.y == pt2.y and abs(pt1.x - pt2.x) == 1))


   def get_image(self, pt):
      return self.background.get_cell(pt).get_image()

   def within_bounds(self, pt):
      return (pt.x >= 0 and pt.x < self.num_cols and
              pt.y >= 0 and pt.y < self.num_rows)
   
   def is_occupied(self, pt):
      return (self.within_bounds(pt) and
              self.occupancy.get_cell(pt) != None)

   def find_nearest(self, pt, type):
      oftype = [(e, distance_sq(pt, e.get_position()))
         for e in self.entities if isinstance(e, type)]
      return nearest_entity(oftype)

   def add_entity(self, entity):
      pt = entity.get_position()
      if self.within_bounds(pt):
         old_entity = self.occupancy.get_cell(pt)
         if old_entity != None:
            old_entity.clear_pending_actions()
         self.occupancy.set_cell(pt, entity)
         self.entities.append(entity)

   def move_entity(self, entity, pt):
      tiles = []
      if self.within_bounds(pt):
         old_pt = entity.get_position()
         self.occupancy.set_cell(old_pt, None)
         tiles.append(old_pt)
         self.occupancy.set_cell(pt, entity)
         tiles.append(pt)
         entity.set_position(pt)
      return tiles

   def remove_entity(self, entity):
      self.remove_entity_at(entity.get_position())

   def remove_entity_at(self, pt):
      if (self.within_bounds(pt) and
         self.occupancy.get_cell(pt) != None):
         entity = self.occupancy.get_cell(pt)
         entity.set_position(point.Point(-1, -1))
         self.occupancy.set_cell(pt, None)

   def schedule_action(self, action, time):
      self.action_queue.insert(action, time)

   def unschedule_action(self, action):
      self.action_queue.remove(action)

   def update_on_time(self, ticks):
      tiles = []

      next = self.action_queue.head()
      while next and next.ord < ticks:
         self.action_queue.pop()
         tiles.extend(next.item(ticks))  # invoke action function
         next = self.action_queue.head()

      return tiles

   def get_background_image(self, pt):
      if self.within_bounds(pt):
         return self.get_image(pt)

   def get_background(self, pt):
      if self.within_bounds(pt):
         return self.background.get_cell(pt)

   def set_background(self, pt, bgnd):
      if self.within_bounds(pt):
         self.background.set_cell(pt, bgnd)

   def get_tile_occupant(self, pt):
      if self.within_bounds(pt):
         return self.occupancy.get_cell(pt)

   def get_entities(self):
      return self.entities

   def next_position(self, entity_pt, dest_pt):
      horiz = self.sign(dest_pt.x - entity_pt.x)
      new_pt = point.Point(entity_pt.x + horiz, entity_pt.y)
 
      if horiz == 0 or self.is_occupied(new_pt):
         vert = self.sign(dest_pt.y - entity_pt.y)
         new_pt = point.Point(entity_pt.x, entity_pt.y + vert)

         if vert == 0 or self.is_occupied(new_pt):
            new_pt = point.Point(entity_pt.x, entity_pt.y)

      return new_pt

   def blob_next_position(self, entity_pt, dest_pt):
      horiz = self.sign(dest_pt.x - entity_pt.x)
      new_pt = point.Point(entity_pt.x + horiz, entity_pt.y)

      if horiz == 0 or (self.is_occupied(new_pt) and
         not isinstance(self.get_tile_occupant(new_pt),
            entities.Ore)):
         vert = self.sign(dest_pt.y - entity_pt.y)
         new_pt = point.Point(entity_pt.x, entity_pt.y + vert)

         if vert == 0 or (self.is_occupied(new_pt) and
            not isinstance(self.get_tile_occupant(new_pt),
            entities.Ore)):
            new_pt = point.Point(entity_pt.x, entity_pt.y)

      return new_pt  

   def miner_to_ore(self, entity, ore):
      entity_pt = entity.get_position()
      if not ore:
         return ([entity_pt], False)
      ore_pt = ore.get_position()
      if self.adjacent(entity_pt, ore_pt):
         entity.set_resource_count(
            1 + entity.get_resource_count())
         ore.remove_entity(self)
         return ([ore_pt], True)
      else:
         new_pt = self.next_position(entity_pt, ore_pt)
         return (self.move_entity(entity, new_pt), False)

   def miner_to_smith(self, entity, smith):
      entity_pt = entity.get_position()
      if not smith:
         return ([entity_pt], False)
      smith_pt = smith.get_position()
      if self.adjacent(entity_pt, smith_pt):
         smith.set_resource_count(
            smith.get_resource_count() +
            entity.get_resource_count())
         entity.set_resource_count(0)
         return ([], True)
      else:
         new_pt = self.next_position(entity_pt, smith_pt)
         return (self.move_entity(entity, new_pt), False)

   def create_miner_not_full_action(self, entity, i_store):
      def action(current_ticks):
         entity.remove_pending_action(action)

         entity_pt = entity.get_position()
         ore = self.find_nearest(entity_pt, entities.Ore)
         (tiles, found) = self.miner_to_ore(entity, ore)

         new_entity = entity
         if found:
            new_entity = entity.try_transform_miner(self,
               entity.try_transform_miner_not_full)
   
         new_entity.schedule_action(self,
            new_entity.create_miner_action(self, i_store),
            current_ticks + new_entity.get_rate())
         return tiles
      return action

   def create_miner_full_action(self, entity, i_store):
      def action(current_ticks):
         entity.remove_pending_action(action)

         entity_pt = entity.get_position()
         smith = self.find_nearest(entity_pt, entities.Blacksmith)
         (tiles, found) = self.miner_to_smith(entity, smith)

         new_entity = entity
         if found:
            new_entity = entity.try_transform_miner(self,
               entity.try_transform_miner_full)
   
         new_entity.schedule_action(self,
            new_entity.create_miner_action(self, i_store),
            current_ticks + new_entity.get_rate())
         return tiles
      return action

   def blob_to_vein(self, entity, vein):
      entity_pt = entity.get_position()
      if not vein:
         return ([entity_pt], False)
      vein_pt = vein.get_position()
      if self.adjacent(entity_pt, vein_pt):
         vein.remove_entity(self)
         return ([vein_pt], True)
      else:
         new_pt = self.blob_next_position(entity_pt, vein_pt)
         old_entity = self.get_tile_occupant(new_pt)
         if isinstance(old_entity, entities.Ore):
            old_entity.remove_entity(self)
         return (self.move_entity(entity, new_pt), False)

   def create_ore_blob_action(self, entity, i_store):
      def action(current_ticks):
         entity.remove_pending_action(action)

         entity_pt = entity.get_position()
         vein = self.find_nearest(entity_pt, entities.Vein)
         (tiles, found) = self.blob_to_vein(entity, vein)

         next_time = current_ticks + entity.get_rate()
         if found:
            quake = self.create_quake(tiles[0], current_ticks, i_store)
            self.add_entity(quake)
            next_time = current_ticks + entity.get_rate() * 2

         entity.schedule_action(self,
            self.create_ore_blob_action(entity, i_store),
            next_time)

         return tiles
      return action

   def find_open_around(self, pt, distance):
      for dy in range(-distance, distance + 1):
         for dx in range(-distance, distance + 1):
            new_pt = point.Point(pt.x + dx, pt.y + dy)

            if (self.within_bounds(new_pt) and
               (not self.is_occupied(new_pt))):
               return new_pt

      return None

   def create_vein_action(self, entity, i_store):
      def action(current_ticks):
         entity.remove_pending_action(action)

         open_pt = self.find_open_around(entity.get_position(),
            entity.get_resource_distance())
         if open_pt:
            ore = self.create_ore(
               "ore - " + entity.get_name() + " - " + str(current_ticks),
            open_pt, current_ticks, i_store)
            self.add_entity(ore)
            tiles = [open_pt]
         else:
            tiles = []

         entity.schedule_action(self,
            self.create_vein_action(entity, i_store),
            current_ticks + entity.get_rate())
         return tiles
      return action

   def create_blob(self, name, pt, rate, ticks, i_store):
      blob = entities.OreBlob(name, pt, rate,
         image_store.get_images(i_store, 'blob'),
         random.randint(BLOB_ANIMATION_MIN, BLOB_ANIMATION_MAX)
         * BLOB_ANIMATION_RATE_SCALE)
      blob.schedule_blob(self, ticks, i_store)
      return blob

   def create_ore(self, name, pt, ticks, i_store):
      ore = entities.Ore(name, pt, image_store.get_images(i_store, 'ore'),
         random.randint(ORE_CORRUPT_MIN, ORE_CORRUPT_MAX))
      ore.schedule_ore(self, ticks, i_store)

      return ore

   def create_quake(self, pt, ticks, i_store):
      quake = entities.Quake("quake", pt,
         image_store.get_images(i_store, 'quake'), QUAKE_ANIMATION_RATE)
      quake.schedule_quake(self, ticks)
      return quake

   def create_vein(self, name, pt, ticks, i_store):
      vein = entities.Vein("vein" + name,
         random.randint(VEIN_RATE_MIN, VEIN_RATE_MAX),
         pt, image_store.get_images(i_store, 'vein'))
      return vein

   def clear_pending_actions(self, entity):
      for action in entity.get_pending_actions():
         self.unschedule_action(action)
      entity.clear_pending_actions()


def nearest_entity(entity_dists):
   if len(entity_dists) > 0:
      pair = entity_dists[0]
      for other in entity_dists:
         if other[1] < pair[1]:
            pair = other
      nearest = pair[0]
   else:
      nearest = None

   return nearest

def distance_sq(p1, p2):
   return (p1.x - p2.x)**2 + (p1.y - p2.y)**2

