"""
Wallet Service.

Provides business logic for wallet management including CRUD operations,
balance management, and escrow operations with proper validation and error handling.
"""

import logging
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.payment_service.models.wallet import Currency, Wallet, WalletStatus
from src.payment_service.schemas.wallet import WalletBalance, WalletCreate, WalletUpdate

logger = logging.getLogger(__name__)


class WalletService:
    """
    Service class for wallet management operations.

    Handles all business logic for wallets including creation, updates,
    balance management, and escrow operations with proper validation.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize wallet service.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        logger.debug("WalletService initialized")

    async def create_wallet(self, wallet_data: WalletCreate) -> Wallet:
        """
        Create a new wallet for a user.

        Args:
            wallet_data: Wallet creation data

        Returns:
            Created wallet instance

        Raises:
            ValueError: If wallet already exists for user or validation fails
        """
        logger.info(
            "Creating new wallet",
            extra={
                "user_id": wallet_data.user_id,
                "currency": wallet_data.currency.value,
                "initial_balance": str(wallet_data.initial_balance),
            },
        )

        # Check if wallet already exists for user
        existing_wallet = await self.get_wallet_by_user_id(wallet_data.user_id)
        if existing_wallet:
            logger.error(
                "Wallet creation failed: wallet already exists",
                extra={"user_id": wallet_data.user_id},
            )
            raise ValueError(f"Wallet already exists for user {wallet_data.user_id}")

        # Create wallet instance
        wallet = Wallet(
            user_id=wallet_data.user_id,
            balance=wallet_data.initial_balance,
            escrow_balance=Decimal("0.0000"),
            currency=wallet_data.currency.value,
            status=WalletStatus.ACTIVE.value,
        )

        self.session.add(wallet)
        await self.session.commit()
        await self.session.refresh(wallet)

        logger.info(
            "Wallet created successfully",
            extra={
                "wallet_id": wallet.id,
                "user_id": wallet.user_id,
                "currency": wallet.currency,
            },
        )

        return wallet

    async def get_wallet(self, wallet_id: str) -> Wallet | None:
        """
        Get a wallet by ID.

        Args:
            wallet_id: Wallet ID

        Returns:
            Wallet instance or None if not found
        """
        logger.debug("Fetching wallet by ID", extra={"wallet_id": wallet_id})

        query = select(Wallet).where(Wallet.id == wallet_id)
        result = await self.session.execute(query)
        wallet = result.scalar_one_or_none()

        if wallet:
            logger.debug(
                "Wallet found",
                extra={
                    "wallet_id": wallet_id,
                    "user_id": wallet.user_id,
                    "balance": str(wallet.balance),
                },
            )
        else:
            logger.warning("Wallet not found", extra={"wallet_id": wallet_id})

        return wallet

    async def get_wallet_by_user_id(self, user_id: str) -> Wallet | None:
        """
        Get a wallet by user ID.

        Args:
            user_id: User ID

        Returns:
            Wallet instance or None if not found
        """
        logger.debug("Fetching wallet by user ID", extra={"user_id": user_id})

        query = select(Wallet).where(Wallet.user_id == user_id)
        result = await self.session.execute(query)
        wallet = result.scalar_one_or_none()

        if wallet:
            logger.debug(
                "Wallet found for user",
                extra={
                    "wallet_id": wallet.id,
                    "user_id": user_id,
                    "balance": str(wallet.balance),
                },
            )
        else:
            logger.warning("Wallet not found for user", extra={"user_id": user_id})

        return wallet

    async def update_wallet(
        self, wallet_id: str, wallet_data: WalletUpdate
    ) -> Wallet | None:
        """
        Update wallet details.

        Args:
            wallet_id: Wallet ID
            wallet_data: Updated wallet data

        Returns:
            Updated wallet instance or None if not found
        """
        logger.info(
            "Updating wallet",
            extra={"wallet_id": wallet_id, "update_data": wallet_data.model_dump()},
        )

        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            logger.warning("Wallet not found for update", extra={"wallet_id": wallet_id})
            return None

        # Update fields if provided
        if wallet_data.status is not None:
            wallet.status = wallet_data.status.value
            logger.info(
                "Wallet status updated",
                extra={
                    "wallet_id": wallet_id,
                    "new_status": wallet.status,
                },
            )

        await self.session.commit()
        await self.session.refresh(wallet)

        logger.info("Wallet updated successfully", extra={"wallet_id": wallet_id})

        return wallet

    async def get_wallet_balance(self, wallet_id: str) -> WalletBalance | None:
        """
        Get wallet balance information.

        Args:
            wallet_id: Wallet ID

        Returns:
            WalletBalance instance or None if not found
        """
        logger.debug("Fetching wallet balance", extra={"wallet_id": wallet_id})

        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            return None

        total_balance = wallet.get_total_balance()

        balance = WalletBalance(
            wallet_id=wallet.id,
            user_id=wallet.user_id,
            balance=wallet.balance,
            escrow_balance=wallet.escrow_balance,
            total_balance=total_balance,
            currency=wallet.currency,
        )

        logger.debug(
            "Wallet balance retrieved",
            extra={
                "wallet_id": wallet_id,
                "balance": str(wallet.balance),
                "escrow_balance": str(wallet.escrow_balance),
                "total_balance": str(total_balance),
            },
        )

        return balance

    async def add_balance(
        self, wallet_id: str, amount: Decimal, description: str | None = None
    ) -> Wallet | None:
        """
        Add balance to wallet.

        Args:
            wallet_id: Wallet ID
            amount: Amount to add (must be positive)
            description: Optional description for logging

        Returns:
            Updated wallet instance or None if not found

        Raises:
            ValueError: If amount is invalid or wallet is not active
        """
        logger.info(
            "Adding balance to wallet",
            extra={
                "wallet_id": wallet_id,
                "amount": str(amount),
                "description": description,
            },
        )

        if amount <= 0:
            logger.error(
                "Invalid amount for adding balance",
                extra={"wallet_id": wallet_id, "amount": str(amount)},
            )
            raise ValueError("Amount must be positive")

        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            logger.warning(
                "Wallet not found for adding balance", extra={"wallet_id": wallet_id}
            )
            return None

        if wallet.status != WalletStatus.ACTIVE.value:
            logger.error(
                "Cannot add balance to inactive wallet",
                extra={"wallet_id": wallet_id, "status": wallet.status},
            )
            raise ValueError(f"Wallet is not active: {wallet.status}")

        wallet.balance += amount

        await self.session.commit()
        await self.session.refresh(wallet)

        logger.info(
            "Balance added successfully",
            extra={
                "wallet_id": wallet_id,
                "amount_added": str(amount),
                "new_balance": str(wallet.balance),
            },
        )

        return wallet

    async def deduct_balance(
        self, wallet_id: str, amount: Decimal, description: str | None = None
    ) -> Wallet | None:
        """
        Deduct balance from wallet.

        Args:
            wallet_id: Wallet ID
            amount: Amount to deduct (must be positive)
            description: Optional description for logging

        Returns:
            Updated wallet instance or None if not found

        Raises:
            ValueError: If amount is invalid, insufficient balance, or wallet is not active
        """
        logger.info(
            "Deducting balance from wallet",
            extra={
                "wallet_id": wallet_id,
                "amount": str(amount),
                "description": description,
            },
        )

        if amount <= 0:
            logger.error(
                "Invalid amount for deducting balance",
                extra={"wallet_id": wallet_id, "amount": str(amount)},
            )
            raise ValueError("Amount must be positive")

        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            logger.warning(
                "Wallet not found for deducting balance", extra={"wallet_id": wallet_id}
            )
            return None

        if not wallet.can_transact(amount):
            logger.error(
                "Cannot deduct balance from wallet",
                extra={
                    "wallet_id": wallet_id,
                    "amount": str(amount),
                    "balance": str(wallet.balance),
                    "status": wallet.status,
                },
            )
            raise ValueError("Insufficient balance or wallet is not active")

        wallet.balance -= amount

        await self.session.commit()
        await self.session.refresh(wallet)

        logger.info(
            "Balance deducted successfully",
            extra={
                "wallet_id": wallet_id,
                "amount_deducted": str(amount),
                "new_balance": str(wallet.balance),
            },
        )

        return wallet

    async def move_to_escrow(
        self, wallet_id: str, amount: Decimal, description: str | None = None
    ) -> Wallet | None:
        """
        Move funds from available balance to escrow.

        Args:
            wallet_id: Wallet ID
            amount: Amount to move to escrow (must be positive)
            description: Optional description for logging

        Returns:
            Updated wallet instance or None if not found

        Raises:
            ValueError: If amount is invalid or insufficient balance
        """
        logger.info(
            "Moving funds to escrow",
            extra={
                "wallet_id": wallet_id,
                "amount": str(amount),
                "description": description,
            },
        )

        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            logger.warning(
                "Wallet not found for escrow operation", extra={"wallet_id": wallet_id}
            )
            return None

        try:
            wallet.move_to_escrow(amount)
        except ValueError as e:
            logger.error(
                "Failed to move funds to escrow",
                extra={
                    "wallet_id": wallet_id,
                    "amount": str(amount),
                    "error": str(e),
                },
            )
            raise

        await self.session.commit()
        await self.session.refresh(wallet)

        logger.info(
            "Funds moved to escrow successfully",
            extra={
                "wallet_id": wallet_id,
                "amount": str(amount),
                "new_balance": str(wallet.balance),
                "new_escrow_balance": str(wallet.escrow_balance),
            },
        )

        return wallet

    async def release_from_escrow(
        self, wallet_id: str, amount: Decimal, description: str | None = None
    ) -> Wallet | None:
        """
        Release funds from escrow to available balance.

        Args:
            wallet_id: Wallet ID
            amount: Amount to release from escrow (must be positive)
            description: Optional description for logging

        Returns:
            Updated wallet instance or None if not found

        Raises:
            ValueError: If amount is invalid or insufficient escrow balance
        """
        logger.info(
            "Releasing funds from escrow",
            extra={
                "wallet_id": wallet_id,
                "amount": str(amount),
                "description": description,
            },
        )

        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            logger.warning(
                "Wallet not found for escrow release", extra={"wallet_id": wallet_id}
            )
            return None

        try:
            wallet.release_from_escrow(amount)
        except ValueError as e:
            logger.error(
                "Failed to release funds from escrow",
                extra={
                    "wallet_id": wallet_id,
                    "amount": str(amount),
                    "error": str(e),
                },
            )
            raise

        await self.session.commit()
        await self.session.refresh(wallet)

        logger.info(
            "Funds released from escrow successfully",
            extra={
                "wallet_id": wallet_id,
                "amount": str(amount),
                "new_balance": str(wallet.balance),
                "new_escrow_balance": str(wallet.escrow_balance),
            },
        )

        return wallet

    async def suspend_wallet(self, wallet_id: str, reason: str | None = None) -> Wallet | None:
        """
        Suspend a wallet.

        Args:
            wallet_id: Wallet ID
            reason: Optional reason for suspension

        Returns:
            Updated wallet instance or None if not found
        """
        logger.warning(
            "Suspending wallet",
            extra={"wallet_id": wallet_id, "reason": reason},
        )

        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            return None

        wallet.status = WalletStatus.SUSPENDED.value

        await self.session.commit()
        await self.session.refresh(wallet)

        logger.warning(
            "Wallet suspended",
            extra={"wallet_id": wallet_id, "reason": reason},
        )

        return wallet

    async def activate_wallet(self, wallet_id: str) -> Wallet | None:
        """
        Activate a suspended wallet.

        Args:
            wallet_id: Wallet ID

        Returns:
            Updated wallet instance or None if not found
        """
        logger.info("Activating wallet", extra={"wallet_id": wallet_id})

        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            return None

        if wallet.status == WalletStatus.CLOSED.value:
            logger.error(
                "Cannot activate closed wallet",
                extra={"wallet_id": wallet_id},
            )
            raise ValueError("Cannot activate closed wallet")

        wallet.status = WalletStatus.ACTIVE.value

        await self.session.commit()
        await self.session.refresh(wallet)

        logger.info("Wallet activated", extra={"wallet_id": wallet_id})

        return wallet

    async def close_wallet(self, wallet_id: str, reason: str | None = None) -> Wallet | None:
        """
        Close a wallet permanently.

        Wallet must have zero balance (both available and escrow) before closing.

        Args:
            wallet_id: Wallet ID
            reason: Optional reason for closure

        Returns:
            Updated wallet instance or None if not found

        Raises:
            ValueError: If wallet has non-zero balance
        """
        logger.warning(
            "Closing wallet",
            extra={"wallet_id": wallet_id, "reason": reason},
        )

        wallet = await self.get_wallet(wallet_id)
        if not wallet:
            return None

        if wallet.balance > 0 or wallet.escrow_balance > 0:
            logger.error(
                "Cannot close wallet with non-zero balance",
                extra={
                    "wallet_id": wallet_id,
                    "balance": str(wallet.balance),
                    "escrow_balance": str(wallet.escrow_balance),
                },
            )
            raise ValueError(
                "Cannot close wallet with non-zero balance. "
                f"Balance: {wallet.balance}, Escrow: {wallet.escrow_balance}"
            )

        wallet.status = WalletStatus.CLOSED.value

        await self.session.commit()
        await self.session.refresh(wallet)

        logger.warning(
            "Wallet closed",
            extra={"wallet_id": wallet_id, "reason": reason},
        )

        return wallet
