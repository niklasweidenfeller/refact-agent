import static org.junit.Assert.*;

import org.junit.Test;


public class GildedRoseTest {

	@Test
	public void testSellInDaysLessThanZeroQualityDegradesTwiceAsFast() {
		Item[] items = new Item[] { new Item("foo", 0, 20) };
		GildedRose app = new GildedRose(items);
		app.updateQuality();
		assertEquals(18, app.items[0].quality);
	}

	@Test
	public void testQualityOfItemIsNeverNegative() {
		Item[] items = new Item[] { new Item("foo", 0, 0) };
		GildedRose app = new GildedRose(items);
		app.updateQuality();
		assertEquals(0, app.items[0].quality);
	}

	@Test
	public void testAgedBrieIncreasesInQuality() {
		Item[] items = new Item[] { new Item("Aged Brie", 10, 20) };
		GildedRose app = new GildedRose(items);
		app.updateQuality();
		assertEquals(21, app.items[0].quality);
	}

	@Test
	public void testQualityOfItemIsNeverMoreThan50() {
		Item[] items = new Item[] { new Item("Aged Brie", 10, 50) };
		GildedRose app = new GildedRose(items);
		app.updateQuality();
		assertEquals(50, app.items[0].quality);
	}

	@Test
	public void testSulfurasNeverHasToBeSoldOrDecreasesInQuality() {
		Item[] items = new Item[] { new Item("Sulfuras, Hand of Ragnaros", 10, 80) };
		GildedRose app = new GildedRose(items);
		app.updateQuality();
		assertEquals(80, app.items[0].quality);
		assertEquals(10, app.items[0].sellIn);
	}
}
