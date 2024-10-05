const { Game } = require('./game.js');

describe("Game Test", function () {
    it("should print the player number to console", function () {
        const game = new Game();
        jest.spyOn(console, 'log');
        game.add('Chet');
        expect(console.log).toHaveBeenCalledWith("Chet was added");
        expect(console.log).toHaveBeenCalledWith("They are player number 1");
        game.add('Pat');
        expect(console.log).toHaveBeenCalledWith("Pat was added");
        expect(console.log).toHaveBeenCalledWith("They are player number 2");
        game.add("Sue");
        expect(console.log).toHaveBeenCalledWith("Sue was added");
        expect(console.log).toHaveBeenCalledWith("They are player number 3");
    });


    it("should move the player", function () {
        const game = new Game();
        jest.spyOn(console, 'log');
        game.add('Chet');
        game.add('Pat');
        game.add('Sue');
        game.roll(1);
        expect(console.log).toHaveBeenCalledWith("Chet is the current player");
        expect(console.log).toHaveBeenCalledWith("They have rolled a 1");
        expect(console.log).toHaveBeenCalledWith("Chet's new location is NaN");
    });


    it("should ask a question", function () {
        const game = new Game();
        game.add('Chet');
        game.add('Pat');
        game.add('Sue');

        jest.spyOn(console, 'log');
        game.roll(1);
        expect(console.log).toHaveBeenCalledWith("Chet is the current player");
        expect(console.log).toHaveBeenCalledWith("They have rolled a 1");
        expect(console.log).toHaveBeenCalledWith("Chet's new location is NaN");
        expect(console.log).toHaveBeenCalledWith("The category is Rock");
        expect(console.log).toHaveBeenCalledWith("Rock Question 0");
    });

    it("Should react to correct answer", function () {
        const game = new Game();
        game.add('Chet');
        game.add('Pat');
        game.add('Sue');
        game.roll(1);
        jest.spyOn(console, 'log');
        game.wasCorrectlyAnswered();
        expect(console.log).toHaveBeenCalledWith("Answer was corrent!!!!");
        expect(console.log).toHaveBeenCalledWith("Chet now has NaN Gold Coins.");
    });

    it("Should react to incorrect answer", function () {
        const game = new Game();
        game.add('Chet');
        game.add('Pat');
        game.add('Sue');
        game.roll(1);
        jest.spyOn(console, 'log');
        game.wrongAnswer();
        expect(console.log).toHaveBeenCalledWith("Question was incorrectly answered");
        expect(console.log).toHaveBeenCalledWith("Chet was sent to the penalty box");
    });
});
