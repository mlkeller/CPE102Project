import actions
import point
import occ_grid

BLOB_RATE_SCALE = 4
BLOB_ANIMATION_RATE_SCALE = 50
BLOB_ANIMATION_MIN = 1
BLOB_ANIMATION_MAX = 3

QUAKE_STEPS = 10
QUAKE_DURATION = 1100
QUAKE_ANIMATION_RATE = 100


#Remove entity - look into when it's used.

class Background(object):
   def __init__(self, name, imgs):
      self.name = name
      self.imgs = imgs
      self.current_img = 0

   def get_name(self):
      return self.get_background(point.Point(col, row))

   def get_images(self):
      return self.imgs

   def get_image(self):
      return self.imgs[self.current_img]


class Obstacle(object):
   def __init__(self, name, position, imgs):
      self.name = name
      self.position = position
      self.imgs = imgs
      self.current_img = 0

   def entity_string(self): 
      return ' '.join(['obstacle', entity.name, str(entity.position.x),
         str(entity.position.y)])

  #possibly move everything below here to "Entity"
   def get_name(self):
      return self.name

   def get_position(self):
      return self.position

   def set_position(self, point):
      self.position = point

   def get_images(self):
      return self.imgs

   def get_image(self):
      return self.imgs[self.current_img]


class Entity(object):
   def __init__(self, name, position, imgs):
      self.name = name
      self.position = position
      self.imgs = imgs
      self.current_img = 0

   def get_name(self):
      return self.name

   def get_position(self):
      return self.position

   def set_position(self, point):
      self.position = point

   def get_images(self):
      return self.imgs

   def get_image(self):
      return self.imgs[self.current_img]


class Animated(object):
   def __init__(self, animation_rate):
      self.animation_rate = animation_rate

   def get_animation_rate(self):
      return self.animation_rate

   def create_animation_action(self, world, repeat_count):
      def action(current_ticks):
         self.remove_pending_action(action)

         self.next_image()

         if repeat_count != 1:
            self.schedule_action(world,
               self.create_animation_action(world, max(repeat_count - 1, 0)),
               current_ticks + self.get_animation_rate())

         return [self.get_position()]
      return action

   def next_image(self):
      self.current_img = (self.current_img + 1) % len(self.imgs)

   def schedule_animation(self, world, repeat_count=0):
      self.schedule_action(world,
         self.create_animation_action(world, repeat_count),
         self.get_animation_rate())


class Actionable(object):
   def __init__(self):
      self.pending_actions = []
   
   def get_pending_actions(self):
      if hasattr(self, "pending_actions"):
         return self.pending_actions
      else:
         return []

   def add_pending_action(self, action):
      if hasattr(self, "pending_actions"):
         self.pending_actions.append(action)

   def remove_pending_action(self, action):
      if hasattr(self, "pending_actions"):
         self.pending_actions.remove(action)

   def clear_pending_actions(self):
      if hasattr(self, "pending_actions"):
         self.pending_actions = []

   def schedule_action(self, world, action, time):
      self.add_pending_action(action)
      world.schedule_action(action, time)


class Miner(Entity, Animated, Actionable):
   def __init__(self, name, position, imgs, animation_rate, rate, resource_limit):
      Entity.__init__(self, name, position, imgs)
      Animated.__init__(self, animation_rate)
      Actionable.__init__(self)
      self.resource_limit = resource_limit
      self.rate = rate

   def get_rate(self):
      return self.rate

   def set_resource_count(self, n):
      self.resource_count = n

   def get_resource_count(self):
      return self.resource_count

   def get_resource_limit(self):
      return self.resource_limit

   def try_transform_miner(self, world, transform):
      new_entity = transform(world)
      if self != new_entity:
         world.clear_pending_actions(self)
         world.remove_entity_at(self.get_position())
         world.add_entity(new_entity)
         new_entity.schedule_animation(world)

      return new_entity

#deal with this??? later??
   def try_transform_miner_full(self, world):
      new_entity = MinerNotFull(
         self.get_name(), self.get_position(),
         self.get_images(), self.get_animation_rate(),
	 self.get_rate(), self.get_resource_limit())

      return new_entity

   def schedule_miner(self, world, ticks, i_store):
      self.schedule_action(world, self.create_miner_action(world, i_store),
         ticks + self.get_rate())
      self.schedule_animation(world)
   

class MinerNotFull(Miner):
   def __init__(self, name, position, imgs, animation_rate, rate, resource_limit):
      Miner.__init__(self, name, position, imgs, animation_rate, rate, resource_limit)
      self.resource_count = 0

   def try_transform_miner_not_full(self, world):
      if self.resource_count < self.resource_limit:
         return self
      else:
         new_entity = MinerFull(
            self.get_name(), self.get_position(),
            self.get_images(), self.get_animation_rate(),
	    self.get_rate(), self.get_resource_limit())
         return new_entity

   def create_miner_action(self, world, image_store):
      return world.create_miner_not_full_action(self, image_store)

   def entity_string(self):
      return ' '.join(['miner', entity.name, str(entity.position.x),
         str(entity.position.y), str(entity.resource_limit),
         str(entity.rate), str(entity.animation_rate)])


class MinerFull(Miner):
   def __init__(self, name, position, imgs, animation_rate, rate, resource_limit):
      Miner.__init__(self, name, position, imgs, animation_rate, rate, resource_limit) 
      self.resource_count = resource_limit

   def try_transform_miner_full(self, world):
      new_entity = MinerNotFull(
         self.get_name(), self.get_position(),
         self.get_images(), self.get_animation_rate(),
	 self.get_rate(), self.get_resource_limit())

      return new_entity

   def create_miner_action(self, world, image_store):
      return world.create_miner_full_action(self, image_store)


class Vein(Entity, Actionable):
   def __init__(self, name, position, imgs, rate, resource_distance=1):
      Entity.__init__(self, name, position, imgs)
      Actionable.__init__(self)
      self.rate = rate
      self.resource_distance = resource_distance

   def entity_string(self):
      return ' '.join(['vein', entity.name, str(entity.position.x),
         str(entity.position.y), str(entity.rate),
         str(entity.resource_distance)])

   def get_rate(self):
      return self.rate

   def get_resource_distance(self):
      return self.resource_distance

   def remove_entity(self, world):
      for action in self.get_pending_actions():
         world.unschedule_action(action)
      self.clear_pending_actions()
      world.remove_entity(self)

   def schedule_vein(self, world, ticks, i_store):
      self.schedule_action(world, world.create_vein_action(self, i_store),
         ticks + self.get_rate())


class Ore(Entity, Actionable):
   def __init__(self, name, position, imgs, rate=5000):
      Entity.__init__(self, name, position, imgs)
      Actionable.__init__(self)
      self.rate = rate

   def entity_string(self):
      return ' '.join(['ore', entity.name, str(entity.position.x),
         str(entity.position.y), str(entity.rate)])

   def get_rate(self):
      return self.rate

   def create_ore_transform_action(self, world, i_store):
      def action(current_ticks):
         self.remove_pending_action(action)
         blob = world.create_blob(self.get_name() + " -- blob",
            self.get_position(),
            self.get_rate() // BLOB_RATE_SCALE,
            current_ticks, i_store)

         self.remove_entity(world)
         world.add_entity(blob)

         return [blob.get_position()]
      return action

   def remove_entity(self, world):
      for action in self.get_pending_actions():
         world.unschedule_action(action)
      self.clear_pending_actions()
      world.remove_entity(self)

   def schedule_ore(self, world, ticks, i_store):
      self.schedule_action(world,
         self.create_ore_transform_action(world, i_store),
         ticks + self.get_rate()) 


class Blacksmith(Entity):
   def __init__(self, name, position, imgs, rate, resource_limit, resource_distance=1):
      Entity.__init__(self, name, position, imgs)
      self.rate = rate
      self.resource_limit = resource_limit
      self.resource_count = 0
      self.resource_distance = resource_distance

   def entity_string(self):
      return ' '.join(['blacksmith', entity.name, str(entity.position.x),
         str(entity.position.y), str(entity.resource_limit),
         str(entity.rate), str(entity.resource_distance)])

   def get_rate(self):
      return self.rate

   def set_resource_count(self, n):
      self.resource_count = n

   def get_resource_count(self):
      return self.resource_count

   def get_resource_limit(self):
      return self.resource_limit

   def get_resource_distance(self):
      return self.resource_distance


class OreBlob(Entity, Animated, Actionable):
   def __init__(self, name, position, imgs, animation_rate, rate):
      Entity.__init__(self, name, position, imgs)
      Animated.__init__(self, animation_rate)
      Actionable.__init__(self)
      self.rate = rate

   def get_rate(self):
      return self.rate

   def schedule_blob(self, world, ticks, i_store):
      self.schedule_action(world, world.create_ore_blob_action(self,
         i_store),
         ticks + self.get_rate())
      self.schedule_animation(world)


class Quake(Entity, Animated, Actionable):

   def __init__(self, name, position, imgs, animation_rate):
      Entity.__init__(self, name, position, imgs)
      Animated.__init__(self, animation_rate)
      Actionable.__init__(self)

   def create_entity_death_action(self, world):
      def action(current_ticks):
         self.remove_pending_action(action)
         pt = self.get_position()
         self.remove_entity(world)
         return [pt]
      return action

   def remove_entity(self, world):
      for action in self.get_pending_actions():
         world.unschedule_action(action)
      self.clear_pending_actions()
      world.remove_entity(self)

   def schedule_quake(self, world, ticks):
      self.schedule_animation(world, QUAKE_STEPS) 
      self.schedule_action(world, self.create_entity_death_action(world),
         ticks + QUAKE_DURATION)

