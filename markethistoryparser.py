import peewee
import json
import re

db = peewee.SqliteDatabase('market.db')


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Item(BaseModel):
    name = peewee.CharField(unique=True, max_length=64)


class Sale(BaseModel):
    item_id = peewee.ForeignKeyField(Item)
    amount = peewee.SmallIntegerField()
    cost = peewee.IntegerField()
    time = peewee.DateTimeField()


db.connect()


def parseEquipContents(contents):
    slotRegex1 = re.compile(r'\((.* slots)\)')
    slotRegex2 = re.compile(r'\((\+\d+\/\d+)\)')
    statsRegex = re.compile(r'\(((?:[A-Z.]+ \+\d+ )+)\)')
    s = []

    # split all matching (parenthises) pairs
    for e in contents.split('('):
        if ')' in e:
            e = '(' + e
        s.append(e)

    # cleanup items
    s = [e.strip() for e in s]

    slots = None
    stats = None

    # find the stats and slots sections
    for e in s[:]:
        m = slotRegex1.match(e)
        if m:
            # slots are bla
            slots = m.group(1)
            s.remove(m.group(0))
            continue

        m = slotRegex2.match(e)
        if m:
            slots = m.group(1)
            s.remove(m.group(0))
            continue

        m = statsRegex.match(e)
        if m:
            stats = m.group(1)
            s.remove(m.group(0))
            continue

    # merge everything else into the name
    # equips are not stackable, so amount would not be merged into the name
    name = ' '.join(s[:])

    return name, stats, slots


def loadDatabase():
    db.drop_tables([Item, Sale])
    db.create_tables([Item, Sale])

    with open('market_history.log', 'r') as f:
        for line in f:
            s = json.loads(line)

            if s['type'] != 'sold':
                print("ignore listing types")
                print(s)
                continue

            style1 = re.compile(r'^\(Channel +\d +FM +\d\) \*\*I just sold a\(n\) (.*) to .* for (.*) mesos!\*\*$')
            style2 = re.compile(r'^\(Channel +\d +FM +\d\) \*\*I just sold a (.*) to .* for (.*) mesos!\*\*$')
            style3 = re.compile(r'^\(Channel +\d +FM +\d\) \*\*I just sold a (.*) for (.*) mesos!\*\*$')
            regexList = [style1, style2, style3]

            for style in regexList:
                matched = style.match(s['content'])

                # found nothing --> try another
                if matched:
                    break

            if matched is None:
                print("problem here (strange input format)")
                print(s)
                continue

            # split item and cost
            item = matched.group(1)
            cost = matched.group(2).replace(',', '')
            amount = 1
            time = s['created_at']
            name = None
            stats = None
            slots = None

            # code to item bunches
            bunchRegex = re.compile(r'(.*) \((\d+)\)$')
            m = bunchRegex.match(item)
            if m:
                # edge case for icarus cape
                if m.group(1) == 'Icarus Cape':
                    pass
                else:
                    # item was sold in a bunch
                    amount = m.group(2)
                    item = m.group(1)

            name = item

            # code to match equips
            # for now ignore equips
            # (since they fluctuate based on price and slots)
            equipRegex = re.compile(r'.*\(.*\)')
            if equipRegex.match(item):
                # item is equip
                # print("Equip: " + item + " | " + cost)
                # parse equip
                # name, stats, slots = parseEquipContents(item)
                continue

            # code to match scrolls
            # old style scrolls are useless (since they miss the %)
            scrollRegex = re.compile('^Scroll for .*[^%]$')
            if scrollRegex.match(item):
                # item is old style scroll
                continue

            # load sale into db
            # WARNING: Race conditions may happen when multithreaded
            obj, created = Item.get_or_create(name=name)

            print("found " + name)
            Sale.create(item_id=obj, amount=amount, cost=cost, time=time)


loadDatabase()
for i in Sale.select().join(Item):
    print(i.time)
