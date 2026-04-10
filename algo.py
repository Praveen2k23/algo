from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass, field
from typing import List
import uuid


# ─────────────────────────────────────────────
# Custom Exceptions
# ─────────────────────────────────────────────

class BankException(Exception):
    """Base exception for all bank errors."""
    pass

class InsufficientFundsError(BankException):
    def __init__(self, balance, amount):
        super().__init__(f"Insufficient funds: balance is ${balance:.2f}, tried to withdraw ${amount:.2f}")

class InvalidAmountError(BankException):
    def __init__(self, amount):
        super().__init__(f"Invalid amount: ${amount}. Must be greater than 0.")

class AccountFrozenError(BankException):
    def __init__(self):
        super().__init__("This account is frozen. No transactions allowed.")


# ─────────────────────────────────────────────
# Transaction Dataclass
# ─────────────────────────────────────────────

@dataclass
class Transaction:
    type: str
    amount: float
    timestamp: datetime = field(default_factory=datetime.now)
    note: str = ""

    def __str__(self):
        return (f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"{self.type.upper():10} | ${self.amount:>10.2f} | {self.note}")


# ─────────────────────────────────────────────
# Abstract Base Class
# ─────────────────────────────────────────────

class Account(ABC):
    _total_accounts = 0  # Class variable shared across all instances

    def __init__(self, owner: str, initial_deposit: float = 0.0):
        if initial_deposit < 0:
            raise InvalidAmountError(initial_deposit)

        Account._total_accounts += 1
        self._account_id: str = str(uuid.uuid4())[:8].upper()
        self._owner: str = owner
        self._balance: float = initial_deposit
        self._transactions: List[Transaction] = []
        self._is_frozen: bool = False

        if initial_deposit > 0:
            self._transactions.append(
                Transaction("deposit", initial_deposit, note="Initial deposit")
            )

    # ── Properties ──────────────────────────

    @property
    def account_id(self):
        return self._account_id

    @property
    def owner(self):
        return self._owner

    @owner.setter
    def owner(self, name: str):
        if not name.strip():
            raise ValueError("Owner name cannot be empty.")
        self._owner = name

    @property
    def balance(self):
        return self._balance

    @property
    def is_frozen(self):
        return self._is_frozen

    # ── Abstract Methods ─────────────────────

    @abstractmethod
    def account_type(self) -> str:
        pass

    @abstractmethod
    def apply_interest(self) -> float:
        pass

    # ── Core Methods ─────────────────────────

    def _validate_transaction(self, amount: float):
        if self._is_frozen:
            raise AccountFrozenError()
        if amount <= 0:
            raise InvalidAmountError(amount)

    def deposit(self, amount: float, note: str = "") -> float:
        self._validate_transaction(amount)
        self._balance += amount
        self._transactions.append(Transaction("deposit", amount, note=note))
        return self._balance

    def withdraw(self, amount: float, note: str = "") -> float:
        self._validate_transaction(amount)
        if amount > self._balance:
            raise InsufficientFundsError(self._balance, amount)
        self._balance -= amount
        self._transactions.append(Transaction("withdrawal", amount, note=note))
        return self._balance

    def freeze(self):
        self._is_frozen = True
        print(f"⚠️  Account {self._account_id} has been FROZEN.")

    def unfreeze(self):
        self._is_frozen = False
        print(f"✅  Account {self._account_id} has been UNFROZEN.")

    def get_statement(self):
        print(f"\n{'='*55}")
        print(f"  {self.account_type()} | Owner: {self._owner} | ID: {self._account_id}")
        print(f"{'='*55}")
        if not self._transactions:
            print("  No transactions yet.")
        for txn in self._transactions:
            print(f"  {txn}")
        print(f"{'─'*55}")
        print(f"  Current Balance: ${self._balance:.2f}")
        print(f"{'='*55}\n")

    # ── Class & Static Methods ────────────────

    @classmethod
    def total_accounts(cls) -> int:
        return cls._total_accounts

    @staticmethod
    def validate_owner_name(name: str) -> bool:
        return isinstance(name, str) and len(name.strip()) > 1

    # ── Dunder Methods ───────────────────────

    def __str__(self):
        status = "🔒 FROZEN" if self._is_frozen else "✅ Active"
        return (f"{self.account_type()} [{self._account_id}] | "
                f"Owner: {self._owner} | Balance: ${self._balance:.2f} | {status}")

    def __repr__(self):
        return f"{self.__class__.__name__}(owner={self._owner!r}, balance={self._balance})"

    def __eq__(self, other):
        return isinstance(other, Account) and self._account_id == other._account_id

    def __lt__(self, other):
        return self._balance < other._balance

    def __add__(self, other):
        """Merge balances conceptually (returns total balance)."""
        if not isinstance(other, Account):
            raise TypeError("Can only add two Account objects.")
        return self._balance + other._balance


# ─────────────────────────────────────────────
# Concrete Subclasses
# ─────────────────────────────────────────────

class SavingsAccount(Account):
    INTEREST_RATE = 0.045  # 4.5% annual

    def __init__(self, owner: str, initial_deposit: float = 0.0):
        super().__init__(owner, initial_deposit)
        self._interest_earned: float = 0.0

    def account_type(self) -> str:
        return "Savings Account"

    def apply_interest(self) -> float:
        interest = round(self._balance * self.INTEREST_RATE, 2)
        self._balance += interest
        self._interest_earned += interest
        self._transactions.append(
            Transaction("interest", interest, note=f"Annual interest @ {self.INTEREST_RATE*100}%")
        )
        return interest

    @property
    def total_interest_earned(self):
        return self._interest_earned


class CheckingAccount(Account):
    def __init__(self, owner: str, initial_deposit: float = 0.0, overdraft_limit: float = 500.0):
        super().__init__(owner, initial_deposit)
        self._overdraft_limit: float = overdraft_limit

    def account_type(self) -> str:
        return "Checking Account"

    def apply_interest(self) -> float:
        return 0.0  # No interest on checking

    def withdraw(self, amount: float, note: str = "") -> float:
        """Overrides base — allows overdraft up to limit."""
        self._validate_transaction(amount)
        if amount > self._balance + self._overdraft_limit:
            raise InsufficientFundsError(self._balance, amount)
        self._balance -= amount
        self._transactions.append(Transaction("withdrawal", amount, note=note))
        if self._balance < 0:
            print(f"⚠️  Overdraft used! Current balance: ${self._balance:.2f}")
        return self._balance


class PremiumAccount(SavingsAccount):
    """Inherits SavingsAccount but with higher interest and perks."""
    INTEREST_RATE = 0.08  # 8%

    def __init__(self, owner: str, initial_deposit: float = 0.0):
        super().__init__(owner, initial_deposit)
        self._perks: List[str] = ["Free transfers", "Priority support", "No fees"]

    def account_type(self) -> str:
        return "Premium Account"

    def list_perks(self):
        print(f"\n🌟 Premium Perks for {self._owner}:")
        for perk in self._perks:
            print(f"   ✔ {perk}")


# ─────────────────────────────────────────────
# Bank Class (Composition)
# ─────────────────────────────────────────────

class Bank:
    def __init__(self, name: str):
        self._name = name
        self._accounts: List[Account] = []

    def open_account(self, account: Account):
        self._accounts.append(account)
        print(f"✅ Opened: {account}")

    def close_account(self, account_id: str):
        for acc in self._accounts:
            if acc.account_id == account_id:
                self._accounts.remove(acc)
                print(f"🗑️  Account {account_id} closed.")
                return
        print(f"Account {account_id} not found.")

    def find_account(self, account_id: str) -> Account:
        for acc in self._accounts:
            if acc.account_id == account_id:
                return acc
        raise BankException(f"No account found with ID: {account_id}")

    def richest_account(self) -> Account:
        return max(self._accounts)

    def total_assets(self) -> float:
        return sum(acc.balance for acc in self._accounts)

    def apply_interest_all(self):
        print("\n💰 Applying interest to all eligible accounts...")
        for acc in self._accounts:
            earned = acc.apply_interest()
            if earned > 0:
                print(f"   {acc.owner}: +${earned:.2f}")

    def __str__(self):
        return (f"\n🏦 {self._name} | Accounts: {len(self._accounts)} | "
                f"Total Assets: ${self.total_assets():,.2f}")


# ─────────────────────────────────────────────
# Main Demo
# ─────────────────────────────────────────────

def main():
    print("\n" + "="*55)
    print("    🏦  ADVANCED PYTHON OOP - BANK SYSTEM DEMO")
    print("="*55)

    bank = Bank("PyBank International")

    # Create accounts
    alice = SavingsAccount("Alice", 5000)
    bob   = CheckingAccount("Bob", 1200, overdraft_limit=300)
    carol = PremiumAccount("Carol", 20000)

    bank.open_account(alice)
    bank.open_account(bob)
    bank.open_account(carol)

    print(bank)

    # Transactions
    print("\n── Transactions ──────────────────────────────")
    alice.deposit(1500, note="Salary")
    alice.withdraw(200, note="Groceries")

    bob.deposit(500, note="Freelance payment")
    bob.withdraw(1800, note="Rent")   # triggers overdraft

    carol.deposit(5000, note="Investment return")
    carol.list_perks()

    # Apply interest
    bank.apply_interest_all()

    # Statements
    alice.get_statement()
    bob.get_statement()
    carol.get_statement()

    # Freeze / Unfreeze
    print("── Freeze Test ───────────────────────────────")
    alice.freeze()
    try:
        alice.withdraw(100)
    except AccountFrozenError as e:
        print(f"❌ Error: {e}")
    alice.unfreeze()
    alice.withdraw(100, note="Post-unfreeze withdrawal")

    # Dunder demos

    print("Learn python")
    print("Hello world")

if __name__ == "__main__":
    main()