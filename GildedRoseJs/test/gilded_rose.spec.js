const { update_quality, Item } = require('../src/gilded_rose');

describe("Gilded Rose", function() {

  it("Once the sell_in days is less then zero, quality degrades twice as fast", function() {
    const items = [new Item("foo", 0, 20)];
    const updatedItems = update_quality(items);
    expect(updatedItems[0].quality).toBe(18);
  });

  it("The quality of an item is never negative", function() {
    const items = [new Item("foo", 0, 0)];
    const updatedItems = update_quality(items);
    expect(updatedItems[0].quality).toBe(0);
  });

  it("'Aged Brie' actually increases in *quality* the older it gets", function() {
    const items = [new Item("Aged Brie", 10, 20)];
    const updatedItems = update_quality(items);
    expect(updatedItems[0].quality).toBe(21);
  });

  it("The quality of an item is never more than 50", function() {
    const items = [new Item("Aged Brie", 10, 50)];
    const updatedItems = update_quality(items);
    expect(updatedItems[0].quality).toBe(50);
  });

  it("'Sulfuras', being a legendary item, never has to be sold or decreases in *quality*", function() {
    const items = [new Item("Sulfuras", 1, 2)];
    const updatedItems = update_quality(items);
    expect(updatedItems[0].quality).toBe(1);
  });

  
});
