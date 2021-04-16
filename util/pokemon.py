import asyncio
import aiohttp
import rapidfuzz
from treelib import Tree
from typing import Optional, Union


"""
Async-ready microwrapper for the pokeapi, does not cover the entire api, only the parts relevant to the pokedex command.
"""

class Pokemon:
    """
    A class representing a pokemon

    Attributes:
        id: int
            The id of the pokemon
        name: str
            The name of the pokemon
        abilities: list[str]
            List containing the names of the abilities the pokemon has
        official_artwork: str
            The url to the official artwork of the default form of the pokemon
        types: list[str]
            A list containing the names of the types the pokemon has, ex: ['flying', 'electric']
        moves: list[str]
            A list containing the names of the moves the pokemon has
        species: Optional[PokemonSpecies]
            PokemonSpecies object containing the species info about the pokemon species
    """
    def __init__(self, data: dict, state):
        self.state = state
        self.id = data['id']
        self.stats = data['stats']
        self.name = data['name']
        self.abilities = [entry['ability']['name'] for entry in data['abilities']]
        self.official_artwork = data['sprites']['other']['official-artwork']['front_default']
        self.types = [entry['type']['name'] for entry in data['types']]
        self.moves = [entry['move']['name'] for entry in data['moves'] if entry.get('move')]
        self.__species_name = data['species']['name']
        self.species: Optional[PokemonSpecies] = None

    async def chunk_species(self):
        """
        Method that fetches a PokemonSpecies and attaches it to instance.
        """
        self.species = await self.state.fetch_pokemon_species(self.__species_name)

class PokemonSpecies:
    """
    Class representing a pokemon species

    Attributes

    id: int
        The id of the pokemon species
    flavor_text_entries: list[str]
        A list containing pokemon flavor text entries
    evolves_from_species: str
        The name of the species whose evolution results in own formation
    legendary: bool
        Boolean indicating whether or not species is legendary
    mythical: bool
        Boolean indicating whether or not species is mythical
    growth_rate: str
        The name of the growth rate, ex slow, fast etc.
    evolution: Optional[PokemonEvolutionChain]
        PokemonEvolutionChain object detailing the evolution tree of the species
    """
    def __init__(self, data, state):
        self.state = state
        self.id = data['id']
        self.flavor_text_entries = [entry['flavor_text'].lower() for entry in data['flavor_text_entries'] if entry['language']['name'] == 'en']
        self.mythical = data.get('is_mythical')
        self.legendary = data.get('is_legendary')
        self.evolves_from = data['evolves_from_species']['name'] if data.get('evolves_from_species') else None
        self.growth_rate = data['growth_rate']['name']
        self.evolves_from_species = data.get('evolves_from_species')
        self.evolution: Optional[PokemonEvolutionChain] = None

        self.__evolution_url = data['evolution_chain']['url']

    async def chunk_evolution(self):
        """
        Method to fetch evolution data for the species and attach it to self instance.
        """
        self.evolution = await self.state.fetch_pokemon_evolution(url=self.__evolution_url)

class PokemonEvolutionChain:
    """
    Class representing a pokemon evolution tree

    Supported operations

    str()
        Returns the evolution tree in a human readable format
    """
    def __init__(self, data):
        self.chain = data['chain']

    def __str__(self):
        temp = self.chain['evolves_to']

        tree = Tree()
        tree.create_node(self.chain['species']['name'], self.chain['species']['name'])

        # Recursively iterates over evolution data and adds it to tree
        def traverse(chain, parent=None):
            for pokemon in chain:
                tree.create_node(pokemon['species']['name'], pokemon['species']['name'], parent=parent)
                traverse(pokemon['evolves_to'], parent=pokemon['species']['name'])

        traverse(temp, parent=self.chain['species']['name'])

        return str(tree)

class PokemonType:
    """
    Class representing a pokemon type

    Attributes

    id: int
        The id of the pokemon type
    name: str
        The name of the pokemon type
    no_damage_to: list[str]
        List containing pokemon type names that self deals no damage to
    half_damage_to: list[str]
        List containing pokemon type names that self deals half damage to
    double_damage_to: list[str]
        List containing pokemon type names that self deals double damage to
    no_damage_from: list[str]
        List containing pokemon type names that self recieves no damage from
    half_damage_from: list[str]
        List containing pokemon type names that self recieves half damage from
    double_damage_from: list[str]
        List containing pokemon type names that self recieves double damage from
    very_strong_against: set[str]
        Set made by concatenating double_damage_to and no_damage_from
    very_weak_against: setp[str]
        Set made by concatenating double_damage_from and no_damage_to
    damage_relations: Mapping[str, list[str]]
        A mapping of relation name (ex: double damage from) to list containing names of types the relation corresponds to
    pokemon: list[str]
        A list of pokemon names that have this type as their slot 1 type
    """
    def __init__(self, data):
        self.id = data['id']
        self.name = data['name']
        self.dr = data['damage_relations']
        self.no_damage_to = [entry['name'] for entry in self.dr['no_damage_to']]
        self.half_damage_to = [entry['name'] for entry in self.dr['half_damage_to']]
        self.double_damage_to = [entry['name'] for entry in self.dr['double_damage_to']]
        self.no_damage_from = [entry['name'] for entry in self.dr['no_damage_from']]
        self.half_damage_from = [entry['name'] for entry in self.dr['half_damage_from']]
        self.double_damage_from = [entry['name'] for entry in self.dr['double_damage_from']]
        self._pokemon = data['pokemon']

    @property
    def pokemon(self):
        return [entry['pokemon']['name'] for entry in self._pokemon if entry['slot'] == 1]

    @property
    def damage_relations(self):
        return {k: [entry['name'] for entry in v] for k, v in self.dr.items()}

    @property
    def very_strong_against(self):
        return set(self.no_damage_from + self.double_damage_to)

    @property
    def very_weak_against(self):
        return set(self.double_damage_from + self.no_damage_to)

class PokemonMove:
    """
    Class representing a pokemon move
    """
    def __init__(self, data, state):
        self.state = state
        self.id = data['id']
        self.name = data['name']
        self.power = data['power']
        self.accuracy = data['accuracy']
        self.type_name = data['type']['name']
        self.type: Optional[PokemonType] = None
        self.effect_chance = data['effect_chance']
        self.__effect_entry = data['effect_entries'][0]['effect']

    @property
    def effect_entry(self):
        if self.effect_chance:
            return self.__effect_entry.replace('$effect_chance', str(self.effect_chance))
        else:
            return self.__effect_entry

    async def chunk_type(self):
        self.type = await self.state.fetch_pokemon_type(self.type_name)


"""
------------------------------------------------------------------------------------------------------------------------
-----------------------------------------------Classes to instantiate---------------------------------------------------
------------------------------------------------------------------------------------------------------------------------
"""


class Client:
    """
    Represents a client that interacts with the pokeapi, if used in the way intended, caches resources upon recieveing
    them and avoids repeated requests till instance is deconstructed
    Method specific usage instructions can be found in their respective docstrings

    Example:

        async def test():
            async with Client() as pokeclient:
                pikachu = await pokeclient.fetch_pokemon('pikachu')
                print(pikachu.species.evolution)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(test())

    Output:

        pichu
        └── pikachu
            └── raichu


    Alternatively, for repeated usage, can be instantiated like usual, note that this method requires calling
    Client.close() after all usage is done.

    Example:

        async def test():
            pokeclient = Client()
            pikachu = await pokeclient.fetch_pokemon('pikachu')
            print(pikachu.species.evolution)

            # Needs to be done manually after all usage is done if instantiating, using the context manager does it for you.
            await pokeclient.close()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(test())

    Output:

        pichu
        └── pikachu
            └── raichu
    """
    def __init__(self, *, session: aiohttp.ClientSession = None):
        self.loop = asyncio.get_event_loop()
        self.session = session
        self.pokecache = {}
        self.species_cache = {}
        self.evolution_cache = {}
        self.type_cache = {}
        self.ability_cache = {}
        self.move_cache = {}
        self.pokemon = {}
        self.moves = {}

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(raise_for_status=False)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def __pre_request_check(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def chunk_pokemon(self):
        """
        Method that requests all pokemon from pokeapi and adds them to internal cache
        """
        await self.__pre_request_check()
        async with self.session.get("https://pokeapi.co/api/v2/pokemon?limit=65535") as r:
            if r.status == 200:
                d = await r.json()
                self.pokemon = {entry['name'] for entry in d['results']}

    async def chunk_moves(self):
        """
        Method that request all pokemon move names and adds them to internal cache
        """
        await self.__pre_request_check()
        async with self.session.get("https://pokeapi.co/api/v2/move?limit=65535") as r:
            if r.status == 200:
                d = await r.json()
                self.moves = {entry['name'] for entry in d['results']}

    @staticmethod
    async def fuzzsearch(query, iterable) -> Union[str, tuple]:
        """
        Does a fuzzy search in an iterable[str] based on the query supplied
        """
        query = query.lower().strip()
        words = [word.strip() for word in query.split(' ') if word.strip()]
        query = '-'.join(words)

        retdict = {}
        retlist = []
        if query in iterable:
            return query
        for elem in iterable:
            if len(query.split('-')) == 1:
                ratio = rapidfuzz.fuzz.ratio(elem, query)
            else:
                ratio = rapidfuzz.fuzz.token_sort_ratio(elem, query)
            if ratio >= 80:
                retdict[elem] = ratio
            elif 50 < ratio < 80:
                retlist.append(elem)
        _max = 0
        max_name = query
        for k, v in retdict.items():
            if v > _max:
                _max = v
                max_name = k
        if retdict:
            return max_name
        else:
            return max_name, sorted(retlist)

    @staticmethod
    def get_endpoint(url):
        """
        Returns the last bit of a url, for example using it on:
        'https:www.google.com/mail/spaghet'
        would return 'spaghet'
        """
        arr = url.split('/')
        ret = [elem for elem in arr if elem]
        return ret[-1]

    async def fetch_pokemon(self, name: str = None, *, chunk=True) -> Optional[Pokemon]:
        """
        Returns a Pokemon based on the name supplied or None, initially looks up cache and only makes api call if
        couldn't find in cache

        Parameters:
            name:str
                name of pokemon to fetch

            chunk: bool
                whether or not to chunk species and evolution for the fetched pokemon, if set to false, Pokemon will
                have the species attribute set to None; defaults to True

        Returns: Optional[Pokemon]
        """
        if name not in self.pokecache:
            await self.__pre_request_check()
            ROUTE = "https://pokeapi.co/api/v2/pokemon/%s" % name.lower()
            async with self.session.get(ROUTE) as r:
                if r.status == 200:
                    d = await r.json()
                    self.pokecache[name.lower()] = Pokemon(d, self)
                    if chunk:
                        await self.pokecache[name.lower()].chunk_species()
                        await self.pokecache[name.lower()].species.chunk_evolution()
        return self.pokecache.get(name.lower())

    async def fetch_pokemon_species(self, name: str) -> Optional[PokemonSpecies]:
        """
        Returns a PokemonSpecies or None, first looks up cache then makes api call if couldn't find the species in cache

        Parameters:
            name: The name of the species to fetch

        Returns:
            Optional[PokemonSpecies]
        """
        if name not in self.species_cache:
            await self.__pre_request_check()
            ROUTE = "https://pokeapi.co/api/v2/pokemon-species/%s" % name.lower()
            async with self.session.get(ROUTE) as r:
                if r.status == 200:
                    d = await r.json()
                    self.species_cache[d['name'].lower()] = PokemonSpecies(d, self)
                else:
                    return None
        return self.species_cache.get(name.lower())

    async def fetch_pokemon_evolution(self, **kwargs) -> Optional[PokemonEvolutionChain]:
        """
        Returns a PokemonEvolution object for a particular id/url supplied as kwarg
        """
        if 'id' in kwargs:
            _id = kwargs['id']
            ROUTE = f"https://pokeapi.co/api/v2/evolution-chain/{kwargs['id']}"
        elif 'url' in kwargs:
            ROUTE = kwargs['url']
            _id = self.get_endpoint(kwargs['url'])
        else:
            raise ValueError("Either id or url required")

        if _id not in self.evolution_cache:
            await self.__pre_request_check()
            async with self.session.get(ROUTE) as r:
                if r.status == 200:
                    d = await r.json()
                    self.evolution_cache[_id] = PokemonEvolutionChain(d)

        return self.evolution_cache.get(_id)

    async def fetch_pokemon_type(self, name: str) -> Optional[PokemonType]:
        """
        Fetches a PokemonType ex: fire, electric, grass or None, first looks up cache and makes api call if couldn't find

        Parameters:
            name: The name of the pokemon type to fetch

        Returns:
            Optional[PokemonSpecies]
        """
        ROUTE = "https://pokeapi.co/api/v2/type/%s" % name.lower()
        if name not in self.type_cache:
            await self.__pre_request_check()
            async with self.session.get(ROUTE) as r:
                if r.status == 200:
                    d = await r.json()
                    self.type_cache[name.lower()] = PokemonType(d)
        return self.type_cache.get(name.lower())

    async def fetch_pokemon_move(self, name: str, *, chunk=True) -> Optional[PokemonMove]:
        """
        Fetches a PokemonMove or None, works by looking up cache and making api call if couldn't find in cache

        Parameters:
            name: str
                The name of the pokemon move to fetch
            chunk: bool
                Whether or not to chunk type, defaults to True, if set to false, move will have the type attribute set to None
        Returns:
            Optional[PokemonMove]
        """
        if name.lower() not in self.move_cache:
            await self.__pre_request_check()
            async with self.session.get("https://pokeapi.co/api/v2/move/%s" % name.lower()) as r:
                if r.status == 200:
                    d = await r.json()
                    pokemove = PokemonMove(d, self)
                    if chunk:
                        await pokemove.chunk_type()
                    self.move_cache[name.lower()] = pokemove
        return self.move_cache.get(name.lower())

    async def fetch_pokemon_ability(self, name):
        raise NotImplementedError()

    async def get_pokemon(self, name, *, exact=False):
        """
        Method that wraps fuzzy searching, and fetching into one.

        Parameters:
            name: The name of the pokemon to search and fetch
            exact: Whether or not it has to be exact, if set to True, skips fuzzy searching and directly attempts fetch

        Returns: Union[Pokemon, list, None]

            Pokemon object returned if fuzzy search was able to pinpoint one value.
            List containing potential matches returned if fuzzy search didn't reach any firm conclusion
            Nonetype returned if exact was set to True and remote returned 404
        """
        if not exact:
            if not self.pokemon:
                await self.chunk_pokemon()

            fuzzresult = await self.fuzzsearch(name, self.pokemon)

            if type(fuzzresult) is str:
                return await self.fetch_pokemon(fuzzresult)
            else:
                return fuzzresult[1]
        else:
            return await self.fetch_pokemon(name)

    async def get_pokemon_move(self, name: str, *, exact: bool = False):
        if not exact:
            if not self.moves:
                await self.chunk_moves()

            fuzzresult = await self.fuzzsearch(name, self.moves)

            if type(fuzzresult) is str:
                return await self.fetch_pokemon_move(fuzzresult)
            else:
                return fuzzresult[1]
        else:
            return await self.fetch_pokemon_move(name)

    async def close(self):
        """
        Closes the client
        """
        if self.session:
            await self.session.close()
